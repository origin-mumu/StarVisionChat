"""
语音转文字服务 (STT)
适配 MiMo mimo-v2.5-asr 语音识别
"""
import base64
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from ..config import settings


class STTService:
    """语音转文字服务"""

    def __init__(self):
        self._audio_buffers: Dict[str, List[bytes]] = {}
        self.client = self._create_client()

    def _create_client(self):
        """创建 MiMo OpenAI 兼容客户端"""
        return AsyncOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL
        )

    def add_chunk(self, session_id: str, audio_base64: str):
        """添加音频片段到缓冲区"""
        if session_id not in self._audio_buffers:
            self._audio_buffers[session_id] = []

        audio_bytes = base64.b64decode(audio_base64)
        self._audio_buffers[session_id].append(audio_bytes)

    async def transcribe(self, session_id: str) -> Optional[str]:
        """
        转录音频缓冲区中的语音

        Returns:
            识别出的文字，如果没有有效音频返回 None
        """
        if session_id not in self._audio_buffers:
            return None

        audio_chunks = self._audio_buffers.pop(session_id)
        if not audio_chunks:
            return None

        # 合并音频片段
        audio_data = b"".join(audio_chunks)

        if len(audio_data) < 1000:  # 太短的音频忽略
            return None

        if not settings.MIMO_API_KEY:
            print("STT 错误: 未配置 MiMo API Key")
            return None

        return await self._transcribe_mimo(audio_data)

    async def _transcribe_mimo(self, audio_data: bytes) -> Optional[str]:
        """
        MiMo ASR 语音识别

        通过 chat/completions 接口，发送 base64 音频进行识别
        """
        try:
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            response = await self.client.chat.completions.create(
                model=settings.ASR_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": f"data:audio/wav;base64,{audio_base64}"
                                }
                            }
                        ]
                    }
                ],
                extra_body={"asr_options": {"language": "auto"}},
                stream=False
            )

            text = response.choices[0].message.content
            return text.strip() if text else None

        except Exception as e:
            print(f"MiMo ASR 错误: {e}")
            return None

    def clear_buffer(self, session_id: str):
        """清空指定会话的音频缓冲区"""
        if session_id in self._audio_buffers:
            del self._audio_buffers[session_id]


# 全局实例
stt_service = STTService()
