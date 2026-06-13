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
                # 累积音频数据（MiMo 模式）
                audio_base64 = msg_data.get("audio")
                if audio_base64:
                    stt_service.add_chunk(session_id, audio_base64)

            elif msg_type == "audio_stream":
                # 实时音频流（Qwen 模式）
                audio_base64 = msg_data.get("audio")
                if audio_base64:
                    asyncio.create_task(
                        handle_qwen_audio_stream(websocket, session, audio_base64)
                    )

            elif msg_type == "image_stream":
                # 实时图像帧（Qwen 模式）
                image_base64 = msg_data.get("image")
                if image_base64:
                    asyncio.create_task(
                        handle_qwen_image_stream(websocket, session, image_base64)
                    )

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
        # 更新模型提供商
        if "model_provider" in config_data:
            settings.MODEL_PROVIDER = config_data["model_provider"]

        # 更新 MiMo 配置
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

        # 更新 Qwen 配置
        if "qwen_api_key" in config_data:
            settings.QWEN_API_KEY = config_data["qwen_api_key"]
        if "qwen_model" in config_data:
            settings.QWEN_MODEL = config_data["qwen_model"]
        if "qwen_voice" in config_data:
            settings.QWEN_VOICE = config_data["qwen_voice"]
        if "qwen_region" in config_data:
            settings.QWEN_REGION = config_data["qwen_region"]

        # 重新初始化所有服务客户端
        from ..services.vision_service import vision_service
        from ..services.llm_service import llm_service
        from ..services.stt_service import stt_service
        from ..services.tts_service import tts_service

        vision_service.client = vision_service._create_client()
        llm_service.client = llm_service._create_client()
        stt_service.client = stt_service._create_client()
        tts_service.client = tts_service._create_client()

        # 重新初始化 Qwen 服务
        from ..services.qwen_service import qwen_realtime_service, qwen_llm_service
        qwen_llm_service.client = qwen_llm_service._create_client()

        # 断开 Qwen Realtime 连接（下次使用时会重新连接）
        if qwen_realtime_service.connected:
            await qwen_realtime_service.close()

        await ws.send_json({
            "type": "config_updated",
            "data": {"success": True, "message": "配置已更新", "provider": settings.MODEL_PROVIDER}
        })

        print(f"配置已更新: 模型={settings.MODEL_PROVIDER}")

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
    from ..config import settings

    try:
        session.status = StatusType.THINKING
        await send_status(ws, StatusType.THINKING, "正在思考...")

        # 添加用户消息到历史
        session.add_turn("user", text)

        # 根据模型提供商选择 LLM 服务
        if settings.MODEL_PROVIDER == "qwen":
            from ..services.qwen_service import qwen_llm_service
            messages = session.get_messages_for_llm()
            response = await qwen_llm_service.chat(messages, image_base64=image_base64)
        else:
            from ..services.llm_service import llm_service
            response = await llm_service.chat(session, image_base64=image_base64)

        # 添加助手回复到历史
        session.add_turn("assistant", response)
        session.update_cost("llm_tokens", len(response) * 2)

        # 发送文字回复
        await ws.send_json({
            "type": MessageType.AI_RESPONSE,
            "data": {"text": response, "is_user": False, "is_streaming": False}
        })

        # 语音合成（Qwen 模式下不需要单独 TTS，Realtime 模式会自带）
        if settings.MODEL_PROVIDER != "qwen":
            from ..services.tts_service import tts_service
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


# ─── Qwen 实时流处理 ───

async def handle_qwen_audio_stream(ws: WebSocket, session, audio_base64: str):
    """处理 Qwen 实时音频流"""
    from ..services.qwen_service import qwen_realtime_service, extract_pcm_from_wav
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen":
        return

    # 如果未连接，建立连接
    if not qwen_realtime_service.connected:
        success = await qwen_realtime_service.connect(
            on_text_delta=lambda text: asyncio.create_task(
                ws.send_json({"type": "qwen_text_delta", "data": {"text": text}})
            ),
            on_audio_delta=lambda audio: asyncio.create_task(
                ws.send_json({"type": "qwen_audio_delta", "data": {"audio": audio}})
            ),
            on_transcript=lambda transcript: asyncio.create_task(
                ws.send_json({"type": "qwen_transcript", "data": {"text": transcript, "is_user": True}})
            ),
            on_response_done=lambda event: asyncio.create_task(
                ws.send_json({"type": "qwen_response_done", "data": {}})
            ),
        )
        if not success:
            await send_error(ws, "QWEN_CONNECT_ERROR", "无法连接到 Qwen 服务")
            return

    # 从 WAV 中提取 PCM 数据再发送
    pcm_base64 = extract_pcm_from_wav(audio_base64)
    await qwen_realtime_service.stream_audio(pcm_base64)


async def handle_qwen_image_stream(ws: WebSocket, session, image_base64: str):
    """处理 Qwen 实时图像流"""
    from ..services.qwen_service import qwen_realtime_service
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen" or not qwen_realtime_service.connected:
        return

    await qwen_realtime_service.append_image(image_base64)
