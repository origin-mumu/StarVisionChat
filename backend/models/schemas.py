"""
数据模型定义
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket 消息类型"""

    # 客户端 -> 服务端
    VIDEO_FRAME = "video_frame"
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_END = "audio_end"
    TEXT_INPUT = "text_input"

    # 服务端 -> 客户端
    AI_RESPONSE = "ai_response"
    AI_AUDIO = "ai_audio"
    AI_AUDIO_END = "ai_audio_end"
    STATUS = "status"
    ERROR = "error"
    COST_UPDATE = "cost_update"


class StatusType(str, Enum):
    """状态类型"""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING_STT = "processing_stt"
    PROCESSING_VISION = "processing_vision"
    THINKING = "thinking"
    SPEAKING = "speaking"


class WSMessage(BaseModel):
    """WebSocket 消息基础模型"""

    type: MessageType
    data: Optional[dict] = None


class VideoFrameData(BaseModel):
    """视频帧数据"""

    image: str = Field(description="Base64 编码的 JPEG 图像")
    timestamp: Optional[float] = None


class AudioChunkData(BaseModel):
    """音频片段数据"""

    audio: str = Field(description="Base64 编码的音频数据")
    sample_rate: int = 16000
    format: str = "pcm"


class TextInputData(BaseModel):
    """文本输入数据"""

    text: str = Field(description="用户输入的文本")


class AIResponseData(BaseModel):
    """AI 回复数据"""

    text: str = Field(description="AI 回复的文本")
    is_streaming: bool = Field(default=False, description="是否为流式片段")


class AIAudioData(BaseModel):
    """AI 音频数据"""

    audio: str = Field(description="Base64 编码的音频数据")
    format: str = "mp3"


class StatusData(BaseModel):
    """状态数据"""

    status: StatusType
    message: Optional[str] = None


class ErrorData(BaseModel):
    """错误数据"""

    code: str
    message: str


class CostData(BaseModel):
    """成本数据"""

    vision_calls: int = 0
    stt_calls: int = 0
    llm_tokens: int = 0
    tts_chars: int = 0
    estimated_cost: float = 0.0


class ConversationTurn(BaseModel):
    """对话轮次"""

    role: str = Field(description="user / assistant")
    content: str = Field(description="对话内容")
    image_description: Optional[str] = Field(default=None, description="当时的画面描述")
