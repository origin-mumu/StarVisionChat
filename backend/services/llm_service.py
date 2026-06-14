"""
大语言模型服务
处理对话生成（适配 MiMo mimo-v2.5 多模态）
支持 Function Calling 工具调用
"""
import json
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings
from ..services.session_manager import Session
from ..services.tool_service import tool_service


class LLMService:
    """大语言模型服务"""

    def __init__(self):
        self.client = self._create_client()

    def _create_client(self):
        """创建 MiMo OpenAI 兼容客户端"""
        return AsyncOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL
        )

    async def chat(self, session: Session, prompt: str = None, image_base64: str = None) -> str:
        """
        生成对话回复（支持多模态输入）

        Args:
            session: 当前会话
            prompt: 额外的提示词（可选）
            image_base64: Base64 编码的图像（可选，用于多模态调用）

        Returns:
            AI 回复文本
        """
        if not settings.MIMO_API_KEY:
            return "（未配置 MiMo API Key，无法生成回复）"

        try:
            # 获取消息列表
            messages = session.get_messages_for_llm()

            # 如果有额外提示词，添加到最后
            if prompt:
                messages.append({"role": "user", "content": prompt})

            # 如果有图像，将最后一条用户消息改为多模态格式
            if image_base64:
                # 确保图像有正确的前缀
                if not image_base64.startswith("data:"):
                    image_url = f"data:image/jpeg;base64,{image_base64}"
                else:
                    image_url = image_base64

                # 找到最后一条用户消息，改为多模态格式
                for msg in reversed(messages):
                    if msg["role"] == "user":
                        original_text = msg["content"]
                        msg["content"] = [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            },
                            {
                                "type": "text",
                                "text": original_text
                            }
                        ]
                        break
                else:
                    # 如果没有用户消息，添加一条带图像的消息
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            },
                            {
                                "type": "text",
                                "text": "请描述你看到的画面。"
                            }
                        ]
                    })

            tools = tool_service.get_definitions()

            # Function Calling 循环（最多 5 轮工具调用）
            for _ in range(5):
                response = await self.client.chat.completions.create(
                    model=settings.CHAT_MODEL,
                    messages=messages,
                    tools=tools,
                    max_tokens=settings.CHAT_MAX_TOKENS,
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
                    print(f"[Tool] {func_name}({args}) => {result[:100]}")

            return msg.content or "（工具调用轮次超限）"

        except Exception as e:
            print(f"LLM 错误: {e}")
            return f"抱歉，生成回复时出现错误：{str(e)}"

    async def chat_stream(self, session: Session):
        """
        流式生成对话回复

        Yields:
            文本片段
        """
        if not settings.MIMO_API_KEY:
            yield "（未配置 MiMo API Key，无法生成回复）"
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
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

        except Exception as e:
            print(f"LLM 流式错误: {e}")
            yield f"抱歉，生成回复时出现错误：{str(e)}"


# 全局实例
llm_service = LLMService()
