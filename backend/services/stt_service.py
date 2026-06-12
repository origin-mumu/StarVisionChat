"""
语音转文字服务 (STT)
支持本地 Whisper 和云端 API
"""
import io
import base64
import tempfile
from typing import Dict, List, Optional
from ..config import settings


class STTService:
    """语音转文字服务"""

    def __init__(self):
        self._audio_buffers: Dict[str, List[bytes]] = {}
        self._whisper_model = None

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

        # 根据配置选择 STT 模式
        if settings.STT_MODE == "local":
            return await self._transcribe_local(audio_data)
        else:
            return await self._transcribe_cloud(audio_data)

    async def _transcribe_local(self, audio_data: bytes) -> Optional[str]:
        """本地 Whisper 转录 (使用 faster-whisper)"""
        try:
            import numpy as np
            from faster_whisper import WhisperModel

            # 加载模型（懒加载）
            if self._whisper_model is None:
                print(f"加载 Whisper 模型: {settings.WHISPER_MODEL}")
                # faster-whisper 使用 CTranslate2，CPU 模式下使用 int8 量化
                self._whisper_model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device="cpu",
                    compute_type="int8"
                )

            # 将 PCM 数据转换为 numpy 数组
            # 假设是 16kHz 16bit 单声道
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # faster-whisper 需要 float32 numpy 数组
            segments, info = self._whisper_model.transcribe(
                audio_np,
                language="zh",
                beam_size=5,
                vad_filter=True  # 启用 VAD 过滤
            )

            # 合并所有片段
            text = " ".join([segment.text for segment in segments]).strip()
            return text if text else None

        except Exception as e:
            print(f"本地 STT 错误: {e}")
            return None

    async def _transcribe_cloud(self, audio_data: bytes) -> Optional[str]:
        """云端 API 转录"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )

            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            # 调用 Whisper API
            with open(temp_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh"
                )

            text = response.text.strip()
            return text if text else None

        except Exception as e:
            print(f"云端 STT 错误: {e}")
            return None

    def clear_buffer(self, session_id: str):
        """清空指定会话的音频缓冲区"""
        if session_id in self._audio_buffers:
            del self._audio_buffers[session_id]


# 全局实例
stt_service = STTService()
