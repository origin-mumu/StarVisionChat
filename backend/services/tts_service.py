"""
文字转语音服务 (TTS)
支持 Edge-TTS 和 OpenAI TTS
"""
import io
import base64
from typing import Optional
from ..config import settings


class TTSService:
    """文字转语音服务"""

    async def synthesize(self, text: str) -> Optional[str]:
        """
        合成语音

        Args:
            text: 要合成的文本

        Returns:
            Base64 编码的音频数据
        """
        if not text:
            return None

        # 根据配置选择 TTS 模式
        if settings.TTS_MODE == "edge":
            return await self._synthesize_edge(text)
        else:
            return await self._synthesize_openai(text)

    async def _synthesize_edge(self, text: str) -> Optional[str]:
        """Edge-TTS 合成（免费）"""
        try:
            import edge_tts
            import asyncio

            communicate = edge_tts.Communicate(text, settings.TTS_VOICE)

            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if audio_data:
                return base64.b64encode(audio_data).decode("utf-8")
            return None

        except Exception as e:
            print(f"Edge-TTS 错误: {e}")
            return None

    async def _synthesize_openai(self, text: str) -> Optional[str]:
        """OpenAI TTS 合成"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )

            response = await client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )

            audio_data = response.content
            return base64.b64encode(audio_data).decode("utf-8")

        except Exception as e:
            print(f"OpenAI TTS 错误: {e}")
            return None


# 全局实例
tts_service = TTSService()
