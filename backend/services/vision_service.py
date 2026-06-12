"""
视觉理解服务
分析摄像头画面内容
"""
import base64
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings


class VisionService:
    """视觉理解服务"""

    def __init__(self):
        self.client = self._create_client()

    def _create_client(self):
        """创建 OpenAI 客户端"""
        return AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    async def analyze_image(self, image_base64: str, prompt: str = None) -> Optional[str]:
        """
        分析图像内容

        Args:
            image_base64: Base64 编码的 JPEG 图像
            prompt: 自定义提示词

        Returns:
            图像描述文本
        """
        if not settings.OPENAI_API_KEY:
            return "（未配置 API Key，无法分析画面）"

        try:
            # 确保图像有正确的前缀
            if not image_base64.startswith("data:"):
                image_url = f"data:image/jpeg;base64,{image_base64}"
            else:
                image_url = image_base64

            # 默认提示词
            if not prompt:
                prompt = "请用简洁的中文描述这张图片中的主要内容，包括主要物体、人物、场景等。如果有什么特别值得注意的地方，也请指出。"

            response = await self.client.chat.completions.create(
                model=settings.VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "low"  # 降低成本
                                }
                            }
                        ]
                    }
                ],
                max_tokens=settings.VISION_MAX_TOKENS
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"视觉分析错误: {e}")
            return None

    async def analyze_image_with_question(self, image_base64: str, question: str) -> Optional[str]:
        """
        针对图像回答特定问题

        Args:
            image_base64: Base64 编码的 JPEG 图像
            question: 用户的问题

        Returns:
            回答文本
        """
        return await self.analyze_image(
            image_base64,
            prompt=f"用户展示了这张图片并问：{question}\n请根据图片内容回答用户的问题。"
        )


# 全局实例
vision_service = VisionService()
