"""
WebSocket 路由
处理实时音视频通信
"""
import json
import uuid
import asyncio
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.session_manager import session_manager
from ..models.schemas import MessageType, StatusType

router = APIRouter()


async def send_status(ws: WebSocket, status: StatusType, message: str = None):
    """发送状态更新"""
    await ws.send_json({
        "type": MessageType.STATUS,
        "data": {"status": status.value, "message": message}
    })


async def send_error(ws: WebSocket, code: str, message: str):
    """发送错误消息"""
    await ws.send_json({
        "type": MessageType.ERROR,
        "data": {"code": code, "message": message}
    })


async def send_cost_update(ws: WebSocket, session):
    """发送成本更新"""
    await ws.send_json({
        "type": MessageType.COST_UPDATE,
        "data": {
            "vision_calls": session.cost_data.vision_calls,
            "stt_calls": session.cost_data.stt_calls,
            "llm_tokens": session.cost_data.llm_tokens,
            "tts_chars": session.cost_data.tts_chars,
            "estimated_cost": round(session.cost_data.estimated_cost, 6)
        }
    })


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 聊天连接"""
    await websocket.accept()

    # 创建会话
    session_id = str(uuid.uuid4())
    session = session_manager.create_session(session_id)

    # 延迟导入服务（避免循环导入）
    from ..services.vision_service import vision_service
    from ..services.stt_service import stt_service
    from ..services.tts_service import tts_service
    from ..services.llm_service import llm_service

    await send_status(websocket, StatusType.IDLE, "已连接，等待交互...")

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            if msg_type == MessageType.VIDEO_FRAME:
                # 处理视频帧（兼容旧接口，可选）
                image_base64 = msg_data.get("image")
                if image_base64:
                    asyncio.create_task(
                        process_vision(websocket, session, image_base64)
                    )

            elif msg_type == MessageType.AUDIO_CHUNK:
                # 累积音频数据
                audio_base64 = msg_data.get("audio")
                if audio_base64:
                    # 添加到 STT 服务的缓冲区
                    stt_service.add_chunk(session_id, audio_base64)

            elif msg_type == MessageType.AUDIO_END:
                # 音频结束，进行识别（可选附带图像帧）
                image_base64 = msg_data.get("image")
                asyncio.create_task(
                    process_speech(websocket, session, image_base64)
                )

            elif msg_type == MessageType.TEXT_INPUT:
                # 文本输入（可选附带图像帧）
                text = msg_data.get("text", "")
                if text:
                    image_base64 = msg_data.get("image")
                    asyncio.create_task(
                        process_text(websocket, session, text, image_base64)
                    )

            elif msg_type == "config_update":
                # 更新配置
                await handle_config_update(websocket, session, msg_data)

    except WebSocketDisconnect:
        print(f"客户端断开连接: {session_id}")
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        await send_error(websocket, "WS_ERROR", str(e))
    finally:
        # 清理会话
        session_manager.remove_session(session_id)


async def handle_config_update(ws: WebSocket, session, config_data: dict):
    """处理配置更新"""
    from ..config import settings

    try:
        # 更新 MiMo 统一配置
        if "api_key" in config_data:
            settings.MIMO_API_KEY = config_data["api_key"]
        if "base_url" in config_data:
            settings.MIMO_BASE_URL = config_data["base_url"]
        if "chat_model" in config_data:
            settings.CHAT_MODEL = config_data["chat_model"]
        if "asr_model" in config_data:
            settings.ASR_MODEL = config_data["asr_model"]
        if "tts_model" in config_data:
            settings.TTS_MODEL = config_data["tts_model"]
        if "tts_voice" in config_data:
            settings.TTS_VOICE = config_data["tts_voice"]

        # 重新初始化所有服务客户端
        from ..services.vision_service import vision_service
        from ..services.llm_service import llm_service
        from ..services.stt_service import stt_service
        from ..services.tts_service import tts_service

        vision_service.client = vision_service._create_client()
        llm_service.client = llm_service._create_client()
        stt_service.client = stt_service._create_client()
        tts_service.client = tts_service._create_client()

        await ws.send_json({
            "type": "config_updated",
            "data": {"success": True, "message": "配置已更新"}
        })

        api_key_preview = settings.MIMO_API_KEY[:8] + "..." if settings.MIMO_API_KEY else "(空)"
        print(f"配置已更新: API Key={api_key_preview}, Base URL={settings.MIMO_BASE_URL}")

    except Exception as e:
        print(f"配置更新错误: {e}")
        await send_error(ws, "CONFIG_ERROR", str(e))


async def process_vision(ws: WebSocket, session, image_base64: str):
    """处理视觉识别（兼容旧接口）"""
    from ..services.vision_service import vision_service

    try:
        session.status = StatusType.PROCESSING_VISION
        await send_status(ws, StatusType.PROCESSING_VISION, "正在分析画面...")

        # 调用视觉服务
        description = await vision_service.analyze_image(image_base64)

        if description:
            session.update_cost("vision")

            # 发送成本更新
            await send_cost_update(ws, session)

        session.status = StatusType.IDLE
        await send_status(ws, StatusType.IDLE)

    except Exception as e:
        print(f"视觉处理错误: {e}")
        session.status = StatusType.IDLE


async def process_speech(ws: WebSocket, session, image_base64: str = None):
    """处理语音识别（可选附带图像帧）"""
    from ..services.stt_service import stt_service
    from ..services.tts_service import tts_service
    from ..services.llm_service import llm_service

    try:
        session.status = StatusType.PROCESSING_STT
        await send_status(ws, StatusType.PROCESSING_STT, "正在识别语音...")

        # 语音识别
        text = await stt_service.transcribe(session.session_id)

        if not text:
            session.status = StatusType.IDLE
            await send_status(ws, StatusType.IDLE, "未识别到有效语音")
            return

        session.update_cost("stt")

        # 显示用户文字
        await ws.send_json({
            "type": MessageType.AI_RESPONSE,
            "data": {"text": text, "is_user": True, "is_streaming": False}
        })

        # 调用 LLM 生成回复
        session.status = StatusType.THINKING
        await send_status(ws, StatusType.THINKING, "正在思考...")

        # 添加用户消息到历史
        session.add_turn("user", text)

        # 生成回复（如果有图像，使用多模态调用）
        response = await llm_service.chat(session, image_base64=image_base64)

        # 添加助手回复到历史
        session.add_turn("assistant", response)
        session.update_cost("llm_tokens", len(response) * 2)  # 粗略估算

        # 发送文字回复
        await ws.send_json({
            "type": MessageType.AI_RESPONSE,
            "data": {"text": response, "is_user": False, "is_streaming": False}
        })

        # 语音合成
        session.status = StatusType.SPEAKING
        await send_status(ws, StatusType.SPEAKING, "正在回复...")

        audio_base64 = await tts_service.synthesize(response)

        if audio_base64:
            session.update_cost("tts_chars", len(response))
            await ws.send_json({
                "type": MessageType.AI_AUDIO,
                "data": {"audio": audio_base64, "format": "mp3"}
            })

        # 发送成本更新
        await send_cost_update(ws, session)

        session.status = StatusType.IDLE
        await send_status(ws, StatusType.IDLE)

    except Exception as e:
        print(f"语音处理错误: {e}")
        session.status = StatusType.IDLE
        await send_error(ws, "STT_ERROR", str(e))


async def process_text(ws: WebSocket, session, text: str, image_base64: str = None):
    """处理文本输入（可选附带图像帧）"""
    from ..services.tts_service import tts_service
    from ..services.llm_service import llm_service

    try:
        session.status = StatusType.THINKING
        await send_status(ws, StatusType.THINKING, "正在思考...")

        # 添加用户消息到历史
        session.add_turn("user", text)

        # 生成回复（如果有图像，使用多模态调用）
        response = await llm_service.chat(session, image_base64=image_base64)

        # 添加助手回复到历史
        session.add_turn("assistant", response)
        session.update_cost("llm_tokens", len(response) * 2)

        # 发送文字回复
        await ws.send_json({
            "type": MessageType.AI_RESPONSE,
            "data": {"text": response, "is_user": False, "is_streaming": False}
        })

        # 语音合成
        session.status = StatusType.SPEAKING
        await send_status(ws, StatusType.SPEAKING, "正在回复...")

        audio_base64 = await tts_service.synthesize(response)

        if audio_base64:
            session.update_cost("tts_chars", len(response))
            await ws.send_json({
                "type": MessageType.AI_AUDIO,
                "data": {"audio": audio_base64, "format": "mp3"}
            })

        # 发送成本更新
        await send_cost_update(ws, session)

        session.status = StatusType.IDLE
        await send_status(ws, StatusType.IDLE)

    except Exception as e:
        print(f"文本处理错误: {e}")
        session.status = StatusType.IDLE
        await send_error(ws, "TEXT_ERROR", str(e))
