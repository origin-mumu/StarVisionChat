"""
Qwen 服务
支持实时语音对话（WebSocket）和文本对话（HTTP API）
"""
import json
import asyncio
import base64
from typing import Optional, Callable, Dict, Any, List
import websockets
from openai import AsyncOpenAI
from ..config import settings
from ..services.tool_service import tool_service


class QwenRealtimeService:
    """Qwen-Omni-Realtime 实时语音服务（WebSocket）"""

    def __init__(self):
        self.ws = None
        self.connected = False
        self._message_handler = None
        self._response_callbacks: Dict[str, Callable] = {}
        self._transcript_buffer = ""  # 用户语音转录缓冲区
        self._audio_buffer_active = False  # 音频缓冲区是否活跃（正在接收音频流）
        self._transcription_event: Optional[asyncio.Event] = None  # 转录完成事件

    async def connect(self, on_text_delta: Callable = None, on_audio_delta: Callable = None,
                      on_transcript: Callable = None, on_response_done: Callable = None):
        """建立 WebSocket 连接到 Qwen-Omni-Realtime 服务"""
        if not settings.QWEN_API_KEY:
            print("Qwen 错误: 未配置 API Key")
            return False

        try:
            # 先关闭旧连接和消息处理任务
            if self._message_handler:
                self._message_handler.cancel()
                try:
                    await self._message_handler
                except asyncio.CancelledError:
                    pass
                self._message_handler = None
            if self.ws:
                try:
                    await self.ws.close()
                except Exception:
                    pass
                self.ws = None

            url = f"{settings.QWEN_WS_URL}?model={settings.QWEN_MODEL}"
            headers = {"Authorization": f"Bearer {settings.QWEN_API_KEY}"}

            print(f"Qwen Realtime 正在连接: {url}")
            self.ws = await websockets.connect(url, additional_headers=headers)
            self.connected = True
            self._audio_buffer_active = False  # 重置音频缓冲区状态

            self._response_callbacks = {
                "on_text_delta": on_text_delta,
                "on_audio_delta": on_audio_delta,
                "on_transcript": on_transcript,
                "on_response_done": on_response_done,
            }

            await self._update_session()
            self._message_handler = asyncio.create_task(self._handle_messages())

            print(f"Qwen Realtime 已连接: {settings.QWEN_MODEL}")
            return True

        except Exception as e:
            print(f"Qwen Realtime 连接错误: {e}")
            self.connected = False
            return False

    async def _update_session(self):
        """配置会话参数（Manual 模式：禁用 VAD，客户端控制提交时机）"""
        event = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": settings.QWEN_VOICE,
                "instructions": settings.SYSTEM_PROMPT,
                "input_audio_format": "pcm",
                "output_audio_format": "pcm",
                "turn_detection": None,
                "input_audio_transcription": {
                    "model": "qwen3-asr-flash-realtime"
                }
            }
        }
        await self._send_event(event)

    async def _send_event(self, event: dict):
        """发送事件到 Qwen 服务"""
        if not self.ws or not self.connected:
            return
        event["event_id"] = f"event_{id(event)}"
        await self.ws.send(json.dumps(event))

    async def stream_audio(self, audio_base64: str):
        """流式发送音频数据（PCM16 16kHz）"""
        self._audio_buffer_active = True
        event = {"type": "input_audio_buffer.append", "audio": audio_base64}
        await self._send_event(event)

    async def append_image(self, image_base64: str):
        """追加图像帧（音频缓冲区活跃时才能发送）"""
        if not self._audio_buffer_active:
            return
        event = {"type": "input_image_buffer.append", "image": image_base64}
        await self._send_event(event)

    async def commit(self):
        """显式提交音频缓冲区（Manual 模式）"""
        self._audio_buffer_active = False
        self._transcription_event = asyncio.Event()
        event = {"type": "input_audio_buffer.commit"}
        await self._send_event(event)

    async def wait_transcription(self, timeout: float = 10.0) -> bool:
        """等待转录完成"""
        if not self._transcription_event:
            return False
        try:
            await asyncio.wait_for(self._transcription_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def create_response(self):
        """请求模型生成回复（Manual 模式）"""
        event = {"type": "response.create"}
        await self._send_event(event)

    async def _handle_messages(self):
        """处理服务端返回的事件"""
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")

                if event_type == "response.audio.delta":
                    callback = self._response_callbacks.get("on_audio_delta")
                    if callback:
                        callback(event["delta"])

                elif event_type == "response.audio_transcript.delta":
                    callback = self._response_callbacks.get("on_text_delta")
                    if callback:
                        callback(event.get("delta", ""))

                elif event_type == "conversation.item.input_audio_transcription.delta":
                    # 用户语音转录流式更新
                    delta = event.get("text", "") or event.get("delta", "")
                    self._transcript_buffer += delta
                    print(f"[Qwen 转录 delta] {delta} | 累积: {self._transcript_buffer}")

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # 用户语音转录完成（使用 completed 的 transcript，如果为空则用 buffer）
                    transcript = event.get("transcript", "") or self._transcript_buffer
                    self._transcript_buffer = ""
                    print(f"[Qwen 转录完成] {transcript}")
                    callback = self._response_callbacks.get("on_transcript")
                    if callback and transcript:
                        callback(transcript)
                    # 通知等待转录的协程
                    if self._transcription_event:
                        self._transcription_event.set()

                elif event_type == "response.done":
                    self._audio_buffer_active = False
                    callback = self._response_callbacks.get("on_response_done")
                    if callback:
                        callback(event)

                elif event_type == "input_audio_buffer.committed":
                    # 服务端确认缓冲区已提交
                    self._audio_buffer_active = False

                elif event_type == "error":
                    print(f"Qwen Realtime 错误: {event.get('error')}")

                elif event_type == "session.created":
                    print(f"Qwen Realtime 会话已创建")

        except websockets.exceptions.ConnectionClosed:
            print("Qwen Realtime 连接已关闭")
        except Exception as e:
            print(f"Qwen Realtime 消息处理错误: {e}")
        finally:
            self.connected = False

    async def close(self):
        """关闭连接"""
        if self._message_handler:
            self._message_handler.cancel()
            try:
                await self._message_handler
            except asyncio.CancelledError:
                pass
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        self.connected = False


class QwenLLMService:
    """Qwen 文本对话服务（HTTP API，兼容 OpenAI 接口）"""

    def __init__(self):
        self.client = self._create_client()

    def _create_client(self):
        """创建 Qwen OpenAI 兼容客户端"""
        return AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    async def chat(self, messages: List[Dict[str, Any]], image_base64: str = None) -> str:
        """
        文本对话（支持 Function Calling）

        Args:
            messages: 消息列表
            image_base64: 可选的图像 base64

        Returns:
            AI 回复文本
        """
        if not settings.QWEN_API_KEY:
            return "（未配置 Qwen API Key）"

        try:
            # 如果有图像，将最后一条用户消息改为多模态格式
            if image_base64:
                if not image_base64.startswith("data:"):
                    image_url = f"data:image/jpeg;base64,{image_base64}"
                else:
                    image_url = image_base64

                for msg in reversed(messages):
                    if msg["role"] == "user":
                        original_text = msg["content"]
                        msg["content"] = [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": original_text}
                        ]
                        break

            tools = tool_service.get_definitions()

            # Function Calling 循环（最多 5 轮工具调用）
            for _ in range(5):
                response = await self.client.chat.completions.create(
                    model="qwen-plus",
                    messages=messages,
                    tools=tools,
                    max_tokens=1024,
                    temperature=0.7
                )

                msg = response.choices[0].message

                # 如果没有工具调用，直接返回文本
                if not msg.tool_calls:
                    return msg.content

                # 执行工具调用
                messages.append(msg.model_dump())
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = await tool_service.execute(func_name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)
                    })
                    print(f"[Qwen Tool] {func_name}({args}) => {str(result)[:100]}")

            return msg.content or "（工具调用轮次超限）"

        except Exception as e:
            print(f"Qwen LLM 错误: {e}")
            return f"抱歉，生成回复时出现错误：{str(e)}"


def extract_pcm_from_wav(wav_base64: str) -> str:
    """从 WAV base64 数据中提取纯 PCM 数据"""
    try:
        wav_bytes = base64.b64decode(wav_base64)
        data_marker = b'data'
        data_start = wav_bytes.find(data_marker)

        if data_start != -1:
            pcm_start = data_start + 8
            pcm_data = wav_bytes[pcm_start:]
            return base64.b64encode(pcm_data).decode('utf-8')
        else:
            pcm_data = wav_bytes[44:]
            return base64.b64encode(pcm_data).decode('utf-8')
    except Exception as e:
        print(f"WAV 解析错误: {e}")
        return wav_base64


# 全局实例
qwen_realtime_service = QwenRealtimeService()
qwen_llm_service = QwenLLMService()
