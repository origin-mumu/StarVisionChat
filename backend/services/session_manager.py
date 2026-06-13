"""
会话管理服务
管理每个 WebSocket 连接的对话上下文和状态
"""
from typing import Dict, List, Optional
from datetime import datetime
from ..models.schemas import ConversationTurn, CostData, StatusType


class Session:
    """单个会话"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.conversation_history: List[ConversationTurn] = []
        self.status: StatusType = StatusType.IDLE
        self.cost_data = CostData()

    def add_turn(self, role: str, content: str, image_description: Optional[str] = None):
        """添加对话轮次"""
        turn = ConversationTurn(
            role=role,
            content=content,
            image_description=image_description
        )
        self.conversation_history.append(turn)

        # 保持历史记录在限制范围内
        from ..config import settings
        if len(self.conversation_history) > settings.MAX_HISTORY_TURNS * 2:
            # 保留最近的对话
            self.conversation_history = self.conversation_history[-(settings.MAX_HISTORY_TURNS * 2):]

    def get_messages_for_llm(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """获取发送给 LLM 的消息列表"""
        from ..config import settings

        messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]

        # 添加历史对话
        recent_history = self.conversation_history[-(max_turns * 2):]
        for turn in recent_history:
            messages.append({"role": turn.role, "content": turn.content})

        return messages

    def update_cost(self, cost_type: str, amount: int = 1):
        """更新成本统计"""
        if cost_type == "vision":
            self.cost_data.vision_calls += amount
            self.cost_data.estimated_cost += 0.0004 * amount  # MiMo 视觉分析
        elif cost_type == "stt":
            self.cost_data.stt_calls += amount
            self.cost_data.estimated_cost += 0.0  # 本地免费
        elif cost_type == "llm_tokens":
            self.cost_data.llm_tokens += amount
            self.cost_data.estimated_cost += (amount / 1000) * 0.0002
        elif cost_type == "tts_chars":
            self.cost_data.tts_chars += amount
            self.cost_data.estimated_cost += 0.0  # MiMo TTS


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self, session_id: str) -> Session:
        """创建新会话"""
        session = Session(session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str):
        """移除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]

    @property
    def active_sessions(self) -> int:
        """活跃会话数"""
        return len(self._sessions)


# 全局会话管理器
session_manager = SessionManager()
