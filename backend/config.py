"""
StarVisionChat 配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """应用配置"""

    # 应用基础配置
    APP_NAME: str = "StarVisionChat"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # OpenAI 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # 视觉模型配置
    VISION_MODEL: str = os.getenv("VISION_MODEL", "gpt-4o-mini")
    VISION_MODEL_STRONG: str = os.getenv("VISION_MODEL_STRONG", "gpt-4o")
    VISION_MAX_TOKENS: int = int(os.getenv("VISION_MAX_TOKENS", "300"))

    # 对话模型配置
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    CHAT_MODEL_STRONG: str = os.getenv("CHAT_MODEL_STRONG", "gpt-4o")
    CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "500"))

    # STT 配置
    STT_MODE: str = os.getenv("STT_MODE", "local")  # local / cloud
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")

    # TTS 配置
    TTS_MODE: str = os.getenv("TTS_MODE", "edge")  # edge / openai
    TTS_VOICE: str = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

    # 帧采样配置
    FRAME_INTERVAL: float = float(os.getenv("FRAME_INTERVAL", "2.0"))  # 秒
    FRAME_QUALITY: int = int(os.getenv("FRAME_QUALITY", "60"))  # JPEG 质量
    FRAME_MAX_WIDTH: int = int(os.getenv("FRAME_MAX_WIDTH", "640"))  # 最大宽度

    # 对话配置
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "10"))
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        """你是一个 AI 视觉对话助手。你能看到用户摄像头中的画面，并与用户进行自然对话。
请用简洁、友好的中文回答用户的问题。如果用户展示了某个物品，请描述你看到的内容。
如果用户问的是与画面无关的问题，也可以正常回答。"""
    )


settings = Settings()
