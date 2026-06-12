"""
大语言模型服务
处理对话生成
"""
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings
from ..services.session_manager import Session


class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.client = self._create_client()

    def _create_client(self):
        """创建 OpenAI 客户端"""
        return AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    async def chat(self, session: Session, prompt: str = None) -> str:
        """
        生成对话回复

        Args:
            session: 当前会话
            prompt: 额外的提示词（可选）

        Returns:
            AI 回复文本
        """
        if not settings.OPENAI_API_KEY:
            return "（未配置 API Key，无法生成回复）"

        try:
            # 获取消息列表
            messages = session.get_messages_for_llm()

            # 如果有额外提示词，添加到最后
            if prompt:
                messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                max_tokens=settings.CHAT_MAX_TOKENS,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"LLM 错误: {e}")
            return f"抱歉，生成回复时出现错误：{str(e)}"

    async def chat_stream(self, session: Session):
        """
        流式生成对话回复

        Yields:
            文本片段
        """
        if not settings.OPENAI_API_KEY:
            yield "（未配置 API Key，无法生成回复）"
            return

        try:
            messages = session.get_messages_for_llm()

            stream = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                max_tokens=settings.CHAT_MAX_TOKENS,
                temperature=0.7,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"LLM 流式错误: {e}")
            yield f"抱歉，生成回复时出现错误：{str(e)}"


# 全局实例
llm_service = LLMService()
