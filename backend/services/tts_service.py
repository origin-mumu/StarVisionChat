"""
文字转语音服务 (TTS)
适配 MiMo mimo-v2.5-tts 语音合成
"""
import io
import base64
import struct
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings


class TTSService:
    """文字转语音服务"""

    def __init__(self):
        self.client = self._create_client()

    def _create_client(self):
        """创建 MiMo OpenAI 兼容客户端"""
        return AsyncOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL
        )

    async def synthesize(self, text: str) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本

        Returns:
            Base64 编码的 WAV 音频数据
        """
        if not text:
            return None

        if not settings.MIMO_API_KEY:
            print("TTS 错误: 未配置 MiMo API Key")
            return None

        return await self._synthesize_mimo(text)

    async def _synthesize_mimo(self, text: str) -> Optional[str]:
        """
        MiMo TTS 语音合成

        通过 chat/completions 接口合成语音，返回 PCM16 数据
        前端需要播放 WAV 格式，这里将 PCM16 转换为 WAV
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.TTS_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": "请用自然流畅的语调朗读以下文本。"
                    },
                    {
                        "role": "assistant",
                        "content": text
                    }
                ],
                extra_body={
                    "audio": {
                        "format": "pcm16",
                        "voice": settings.TTS_VOICE
                    }
                },
                stream=False
            )

            # 获取音频数据
            message = response.choices[0].message
            if not hasattr(message, 'audio') or not message.audio:
                print("TTS 警告: 响应中没有音频数据")
                return None

            audio_data = message.audio.data  # base64 编码的 PCM16

            # PCM16 → WAV 转换
            pcm_bytes = base64.b64decode(audio_data)
            wav_bytes = self._pcm_to_wav(pcm_bytes, sample_rate=24000, channels=1, bits=16)

            return base64.b64encode(wav_bytes).decode("utf-8")

        except Exception as e:
            print(f"MiMo TTS 错误: {e}")
            return None

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
        """
        将 PCM16 原始数据转换为 WAV 格式

        Args:
            pcm_data: PCM16 原始字节
            sample_rate: 采样率（MiMo TTS 默认 24kHz）
            channels: 声道数
            bits: 位深

        Returns:
            WAV 格式字节数据
        """
        byte_rate = sample_rate * channels * (bits // 8)
        block_align = channels * (bits // 8)
        data_size = len(pcm_data)

        # WAV 文件头
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',                    # ChunkID
            36 + data_size,             # ChunkSize
            b'WAVE',                    # Format
            b'fmt ',                    # Subchunk1ID
            16,                         # Subchunk1Size (PCM)
            1,                          # AudioFormat (PCM = 1)
            channels,                   # NumChannels
            sample_rate,                # SampleRate
            byte_rate,                  # ByteRate
            block_align,                # BlockAlign
            bits,                       # BitsPerSample
            b'data',                    # Subchunk2ID
            data_size                   # Subchunk2Size
        )

        return wav_header + pcm_data


# 全局实例
tts_service = TTSService()
