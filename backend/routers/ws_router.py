"""
WebSocket 路由
处理实时音视频通信
"""
import re
import json
import uuid
import asyncio
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.session_manager import session_manager
from ..models.schemas import MessageType, StatusType

router = APIRouter()


def strip_markdown(text: str) -> str:
    """清理 Markdown 格式，保留纯文本用于 TTS 合成"""
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).replace('```', ''), text)  # 代码块内容保留
    text = re.sub(r'```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)        # 行内代码
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # 标题
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # 加粗
    text = re.sub(r'\*([^*]+)\*', r'\1', text)       # 斜体
    text = re.sub(r'__([^_]+)__', r'\1', text)       # 加粗
    text = re.sub(r'_([^_]+)_', r'\1', text)         # 斜体
    text = re.sub(r'~~([^~]+)~~', r'\1', text)       # 删除线
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)  # 引用
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)  # 无序列表
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # 有序列表
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # 链接
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)  # 图片
    text = re.sub(r'\|', ' ', text)                  # 表格竖线
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)  # 分割线
    text = re.sub(r'\n{3,}', '\n\n', text)           # 多空行
    return text.strip()


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

            elif msg_type == "audio_end_qwen":
                # Qwen 模式：录音结束，提交缓冲区并请求模型响应
                asyncio.create_task(
                    handle_qwen_audio_end(websocket, session)
                )

            elif msg_type == "qwen_scene_switch":
                # Qwen 模式：场景切换，打断当前回复并用新场景重新生成
                scene_prompt = msg_data.get("system_prompt", "")
                if scene_prompt:
                    asyncio.create_task(
                        handle_qwen_scene_switch(websocket, session, scene_prompt)
                    )

            elif msg_type == MessageType.AUDIO_END:
                # 音频结束，进行识别（可选附带图像帧 + 场景数据）
                image_base64 = msg_data.get("image")
                scenes = msg_data.get("scenes", [])
                current_scene = msg_data.get("current_scene", "")
                asyncio.create_task(
                    process_speech(websocket, session, image_base64, scenes, current_scene)
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

            elif msg_type == "scene_update":
                # 更新场景模式（系统提示词）
                system_prompt = msg_data.get("system_prompt")
                if system_prompt:
                    from ..config import settings
                    settings.SYSTEM_PROMPT = system_prompt
                    print(f"场景提示词已更新: {system_prompt[:50]}...")

            elif msg_type == "scene_monitor":
                # 场景监控：定期分析画面，AI 判断是否切换场景 + 手势识别
                image_base64 = msg_data.get("image")
                scenes = msg_data.get("scenes", [])
                current_scene = msg_data.get("current_scene", "")
                is_locked = msg_data.get("is_locked", False)
                if image_base64:
                    asyncio.create_task(
                        handle_scene_monitor(websocket, image_base64, scenes, current_scene, is_locked)
                    )

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


async def process_speech(ws: WebSocket, session, image_base64: str = None, scenes: list = None, current_scene: str = ""):
    """处理语音识别（可选附带图像帧 + 场景数据）"""
    from ..services.stt_service import stt_service
    from ..services.tts_service import tts_service
    from ..services.llm_service import llm_service
    from ..config import settings

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

        # ── 场景关键词检测（在调 LLM 之前）──
        if scenes:
            text_lower = text.lower()
            for scene in scenes:
                keywords = scene.get("keywords", [])
                if any(kw in text_lower for kw in keywords):
                    scene_id = scene.get("id", "")
                    scene_name = scene.get("name", "")
                    scene_prompt = scene.get("systemPrompt", "")
                    if scene_id and scene_id != current_scene and scene_prompt:
                        settings.SYSTEM_PROMPT = scene_prompt
                        await ws.send_json({
                            "type": "scene_detected",
                            "data": {"scene": scene_id, "name": scene_name}
                        })
                        print(f"[Scene] 语音检测到场景切换: {scene_name}")
                    break

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

        audio_base64 = await tts_service.synthesize(strip_markdown(response))

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
        # 先检测记忆/提醒意图
        from ..services.memory_interceptor import process_user_message
        memory_result = process_user_message(text)
        if memory_result:
            await ws.send_json({
                "type": "memory_saved",
                "data": {"message": memory_result}
            })

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

            audio_base64 = await tts_service.synthesize(strip_markdown(response))

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
# 连接锁：防止多个音频块同时尝试连接
_qwen_connecting = False


async def ensure_qwen_connected(ws: WebSocket) -> bool:
    """确保 Qwen 服务已连接（带锁防止并发连接）"""
    global _qwen_connecting
    from ..services.qwen_service import qwen_realtime_service

    if qwen_realtime_service.connected:
        return True

    if _qwen_connecting:
        # 另一个块正在连接中，跳过
        return False

    _qwen_connecting = True
    try:
        def _on_transcript(transcript):
            """转录回调：发送到前端 + 自动提取记忆"""
            asyncio.create_task(
                ws.send_json({"type": "qwen_transcript", "data": {"text": transcript, "is_user": True}})
            )
            # 自动检测记忆/提醒意图
            from ..services.memory_interceptor import process_user_message
            result = process_user_message(transcript)
            if result:
                print(f"[Memory] {result}")
                asyncio.create_task(
                    ws.send_json({"type": "memory_saved", "data": {"message": result}})
                )

        success = await qwen_realtime_service.connect(
            on_text_delta=lambda text: asyncio.create_task(
                ws.send_json({"type": "qwen_text_delta", "data": {"text": text}})
            ),
            on_audio_delta=lambda audio: asyncio.create_task(
                ws.send_json({"type": "qwen_audio_delta", "data": {"audio": audio}})
            ),
            on_transcript=_on_transcript,
            on_response_done=lambda event: asyncio.create_task(
                ws.send_json({"type": "qwen_response_done", "data": {}})
            ),
        )
        if not success:
            await send_error(ws, "QWEN_CONNECT_ERROR", "无法连接到 Qwen 服务")
        return success
    finally:
        _qwen_connecting = False


async def handle_qwen_audio_stream(ws: WebSocket, session, audio_base64: str):
    """处理 Qwen 实时音频流"""
    from ..services.qwen_service import qwen_realtime_service, extract_pcm_from_wav
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen":
        return

    # 确保已连接（带锁，不会并发重连）
    if not await ensure_qwen_connected(ws):
        return

    try:
        pcm_base64 = extract_pcm_from_wav(audio_base64)
        await qwen_realtime_service.stream_audio(pcm_base64)
    except Exception:
        # 连接已断开，静默丢弃后续音频块（不要每块都尝试重连）
        pass


# Qwen 视觉响应计数：累计 N 帧后自动触发描述（不依赖语音）
_qwen_image_count = 0
_QWEN_VISION_INTERVAL = 10  # 每 10 帧触发一次视觉描述


async def handle_qwen_image_stream(ws: WebSocket, session, image_base64: str):
    """处理 Qwen 实时图像流"""
    from ..services.qwen_service import qwen_realtime_service
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen" or not qwen_realtime_service.connected:
        return

    global _qwen_image_count
    try:
        await qwen_realtime_service.append_image(image_base64)
        _qwen_image_count += 1

        # 累计足够帧数后，触发 AI 描述画面（不依赖语音）
        if _qwen_image_count >= _QWEN_VISION_INTERVAL:
            _qwen_image_count = 0
            await qwen_realtime_service.create_response()
    except Exception:
        pass


async def handle_qwen_audio_end(ws: WebSocket, session):
    """Qwen Manual 模式：录音结束 → 提交缓冲区 → 等待转录 → 请求模型响应"""
    from ..services.qwen_service import qwen_realtime_service
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen" or not qwen_realtime_service.connected:
        return

    global _qwen_image_count
    _qwen_image_count = 0  # 重置视觉计数器，避免重复触发

    try:
        # 1. 显式提交音频缓冲区
        await qwen_realtime_service.commit()
        # 2. 等待转录完成
        await qwen_realtime_service.wait_transcription(timeout=10)
        # 3. 请求模型响应
        await qwen_realtime_service.create_response()
    except Exception as e:
        print(f"Qwen audio end 处理错误: {e}")


async def handle_qwen_scene_switch(ws: WebSocket, session, system_prompt: str):
    """Qwen 模式：场景切换 — 打断当前回复，更新提示词，重新生成"""
    from ..services.qwen_service import qwen_realtime_service
    from ..config import settings

    if settings.MODEL_PROVIDER != "qwen" or not qwen_realtime_service.connected:
        return

    try:
        # 1. 打断当前回复
        await qwen_realtime_service.cancel_response()
        # 2. 更新系统提示词
        settings.SYSTEM_PROMPT = system_prompt
        await qwen_realtime_service.update_instructions(system_prompt)
        # 3. 重新生成回复
        await qwen_realtime_service.create_response()
        print(f"[Qwen] 场景切换完成，重新生成回复")
    except Exception as e:
        print(f"Qwen 场景切换错误: {e}")


# ─── 场景监控 ───
_scene_cache = {"last_scene": ""}


async def handle_scene_monitor(ws: WebSocket, image_base64: str, scenes: list, current_scene: str, is_locked: bool = False):
    """场景监控 + 手势识别：根据锁定状态使用不同 prompt（MiMo & Qwen 通用）"""
    from openai import AsyncOpenAI
    from ..config import settings

    if not scenes:
        return

    scene_names = [s.get("name", "") for s in scenes if s.get("name")]
    scene_list_str = "、".join(scene_names)

    try:
        # 根据模型提供商选择 client
        if settings.MODEL_PROVIDER == "qwen":
            if not settings.QWEN_API_KEY:
                return
            client = AsyncOpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            model = "qwen3.6-flash"
        else:
            # MiMo
            key = settings.MIMO_API_KEY
            if not key:
                return
            client = AsyncOpenAI(
                api_key=key,
                base_url=settings.MIMO_BASE_URL
            )
            model = settings.CHAT_MODEL or "mimo-v2.5"

        if is_locked:
            # ── 锁定状态：只检测剪刀手解锁手势 ──
            prompt = """你是一个视觉分析助手。当前系统处于锁定状态。
观察画面中是否有剪刀手或V字手势（食指和中指张开，其余手指收拢）。
- 如果有剪刀手/V字手势，回复：解锁
- 如果没有，回复：无"""
            user_text = "画面中是否有剪刀手或V字手势？"
            max_t = 10
        else:
            # ── 未锁定状态：先检测大拇指锁定，没有则判断场景 ──
            prompt = f"""你是一个视觉分析助手。完成以下两步：

第一步：观察画面中是否有竖大拇指手势（握拳，拇指朝上伸出）。
- 如果有，回复：锁定
- 如果没有，继续第二步。

第二步：判断当前最适合的场景。
可选场景：{scene_list_str}
当前场景：{current_scene}
- 如果不变，回复：不变
- 如果适合其他场景，回复场景名称。

回复格式（严格遵守）：
<锁定/不变/场景名称>"""
            user_text = "分析画面，判断手势和场景。"
            max_t = 20

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": user_text}
                ]}
            ],
            max_tokens=max_t,
        )
        result = response.choices[0].message.content.strip()

        if is_locked:
            # 锁定状态：只关心"解锁"
            if "解锁" in result or result.lower().startswith("unlock"):
                await ws.send_json({"type": "gesture_result", "data": {"result": "unlock"}})
                print(f"[Gesture] 检测到解锁手势")
        else:
            # 未锁定状态：先看是否锁定，再看场景
            if "锁定" in result or result.lower().startswith("lock"):
                await ws.send_json({"type": "gesture_result", "data": {"result": "lock"}})
                print(f"[Gesture] 检测到锁定手势")
            elif result and result != "不变" and result != current_scene:
                matched = next((s for s in scenes if s.get("name") == result), None)
                if matched and result != _scene_cache["last_scene"]:
                    _scene_cache["last_scene"] = result
                    await ws.send_json({
                        "type": "scene_detected",
                        "data": {"scene": matched["id"], "name": result}
                    })
                    print(f"[Scene] AI 建议切换: {result}")
            else:
                _scene_cache["last_scene"] = current_scene

    except Exception as e:
        err = str(e)
        if not any(x in err for x in ('401', '403', '404', 'invalid_api_key', 'model_not_found')):
            print(f"场景监控错误: {e}")


# ═══════════════════════════════════════════
#  WebRTC 信令中继 — 手机摄像头 → PC
# ═══════════════════════════════════════════
# 内存字典：{ session_id: { "phone": ws, "pc": ws } }
camera_sessions = {}


@router.websocket("/ws/camera")
async def websocket_camera(websocket: WebSocket):
    """WebRTC 信令中继 — 手机摄像头与 PC 之间的 SDP/ICE 转发"""
    await websocket.accept()
    my_session = None
    my_role = None

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            msg_data = data.get("data", {})

            if msg_type == "camera_register":
                # 手机端注册
                sid = msg_data.get("session")
                if sid:
                    my_session = sid
                    my_role = "phone"
                    if sid not in camera_sessions:
                        camera_sessions[sid] = {}
                    camera_sessions[sid]["phone"] = websocket
                    await websocket.send_json({"type": "camera_registered", "data": {}})
                    print(f"[Camera] 手机已注册: {sid}")

            elif msg_type == "camera_connect":
                # PC 端连接，等待信令
                sid = msg_data.get("session")
                if sid:
                    my_session = sid
                    my_role = "pc"
                    if sid not in camera_sessions:
                        camera_sessions[sid] = {}
                    camera_sessions[sid]["pc"] = websocket
                    phone_ws = camera_sessions[sid].get("phone")
                    if phone_ws:
                        await websocket.send_json({"type": "camera_ready", "data": {"session": sid}})
                        await phone_ws.send_json({"type": "camera_start", "data": {}})
                    print(f"[Camera] PC 已连接: {sid}")

            elif msg_type in ("webrtc_offer", "webrtc_answer", "webrtc_ice"):
                # 转发 SDP / ICE 给对方
                if not my_session:
                    continue
                session_entry = camera_sessions.get(my_session, {})
                target = "pc" if my_role == "phone" else "phone"
                target_ws = session_entry.get(target)
                if target_ws:
                    # 稍作转换以统一格式
                    if msg_type == "webrtc_offer":
                        await target_ws.send_json({"type": "webrtc_offer", "data": msg_data.get("sdp")})
                    elif msg_type == "webrtc_answer":
                        await target_ws.send_json({"type": "webrtc_answer", "data": msg_data.get("sdp")})
                    elif msg_type == "webrtc_ice":
                        await target_ws.send_json({"type": "webrtc_ice", "data": msg_data.get("candidate")})

    except Exception as e:
        print(f"[Camera] 连接异常: {e}")
    finally:
        # 清理
        if my_session and my_session in camera_sessions:
            entry = camera_sessions[my_session]
            if my_role == "phone":
                pc_ws = entry.get("pc")
                if pc_ws:
                    try: await pc_ws.send_json({"type": "camera_disconnect", "data": {}})
                    except: pass
            entry.pop(my_role, None)
            if not entry:
                camera_sessions.pop(my_session, None)
            print(f"[Camera] {my_role} 断开: {my_session}")
