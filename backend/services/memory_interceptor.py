"""
记忆拦截器
通过关键词匹配自动从用户对话中提取记忆和提醒
不依赖 LLM Function Calling，适用于 Qwen Realtime 模式
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from ..services import memory_service

# ─── 记忆关键词 ───
MEMORY_PATTERNS = [
    # 直接记忆指令
    r"帮[我你]记[一下住]*[：:]*\s*(.+)",
    r"记[得住]住?[：:]*\s*(.+)",
    r"别忘[了记][：:]*\s*(.+)",
    r"不要忘[了记][：:]*\s*(.+)",
    r"帮我记住[：:]*\s*(.+)",
    r"记下来[：:]*\s*(.+)",
    r"备忘[：:]*\s*(.+)",
]

# ─── 提醒关键词 ───
REMINDER_PATTERNS = [
    r"提醒[我你][：:]*\s*(.+)",
    r"明天[有要](.+)",
    r"后天[有要](.+)",
    r"下周[有要](.+)",
    r"(\d+)[点时:：](\d*)\s*有(.+)",
    r"(\d+)月(\d+)[日号]\s*有(.+)",
]

# ─── 时间解析 ───
TIME_PATTERNS = [
    (r"明天", lambda: (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")),
    (r"后天", lambda: (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")),
    (r"今天", lambda: datetime.now().strftime("%Y-%m-%d")),
    (r"大后天", lambda: (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")),
]


def _adjust_hour(hour_str: str, text: str) -> int:
    """
    根据上下文调整小时数
    - 有"凌晨/早上/上午" → 24小时制不变
    - 有"下午/晚上/晚" → +12
    - 无明确标识且 1-6 点 → 视为下午 (+12)
    - 无明确标识且 7-12 点 → 视为上午（不变）
    """
    h = int(hour_str)
    if any(w in text for w in ["凌晨", "早上", "上午", "早"]):
        return h
    if any(w in text for w in ["下午", "晚上", "晚", "午后"]):
        return h + 12 if h < 12 else h
    # 无明确标识：1-6 点默认为下午（开会/约定场景）
    if 1 <= h <= 6:
        return h + 12
    return h


def _parse_time(text: str) -> Optional[str]:
    """从文本中提取时间信息"""
    # 检查 "明天/后天" + "X点"
    for pattern, date_fn in TIME_PATTERNS:
        if re.search(pattern, text):
            date_str = date_fn()
            # 尝试提取具体时间
            time_match = re.search(r"(\d{1,2})[点时:：](\d{0,2})", text)
            if time_match:
                hour = _adjust_hour(time_match.group(1), text)
                minute = time_match.group(2) or "00"
                return f"{date_str} {hour:02d}:{minute.zfill(2)}"
            return f"{date_str}"

    # 检查 "X月X日"
    md_match = re.search(r"(\d{1,2})月(\d{1,2})[日号]", text)
    if md_match:
        month = md_match.group(1).zfill(2)
        day = md_match.group(2).zfill(2)
        year = datetime.now().year
        time_match = re.search(r"(\d{1,2})[点时:：](\d{0,2})", text)
        if time_match:
            hour = _adjust_hour(time_match.group(1), text)
            minute = time_match.group(2) or "00"
            return f"{year}-{month}-{day} {hour:02d}:{minute.zfill(2)}"
        return f"{year}-{month}-{day}"

    # 检查纯时间 "X点"
    time_match = re.search(r"(\d{1,2})[点时:：](\d{0,2})\s*(.*)", text)
    if time_match:
        hour = _adjust_hour(time_match.group(1), text)
        minute = time_match.group(2) or "00"
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today} {hour:02d}:{minute.zfill(2)}"

    return None


def _extract_memory(text: str) -> Optional[str]:
    """尝试从文本中提取记忆内容"""
    for pattern in MEMORY_PATTERNS:
        match = re.search(pattern, text)
        if match:
            content = match.group(1).strip()
            # 去掉末尾标点
            content = content.rstrip("。，,. ")
            if len(content) >= 2:
                return content
    return None


def _extract_reminder(text: str) -> Optional[Tuple[str, Optional[str]]]:
    """尝试从文本中提取提醒内容和时间"""
    for pattern in REMINDER_PATTERNS:
        match = re.search(pattern, text)
        if match:
            content = match.group(match.lastindex).strip()
            content = content.rstrip("。，,. ")
            remind_at = _parse_time(text)
            if len(content) >= 2:
                return (content, remind_at)
    return None


def _detect_category(text: str) -> str:
    """根据内容推断记忆分类"""
    if any(w in text for w in ["喜欢", "偏好", "习惯", "爱", "讨厌", "不喜欢"]):
        return "preference"
    if any(w in text for w in ["我是", "我叫", "我在", "我会", "我能"]):
        return "fact"
    if any(w in text for w in ["要", "打算", "计划", "准备"]):
        return "todo"
    return "fact"


def process_user_message(text: str, scene_description: str = None) -> Optional[str]:
    """
    处理用户消息，自动提取记忆/提醒

    Args:
        text: 用户说的话
        scene_description: 当前摄像头画面描述（可选）

    Returns:
        如果保存了记忆，返回确认消息；否则返回 None
    """
    if not text or len(text.strip()) < 2:
        return None

    text = text.strip()

    # 检查是否是记忆指令
    memory_content = _extract_memory(text)
    if memory_content:
        category = _detect_category(text)
        tags = ""
        if scene_description:
            tags = f"场景:{scene_description[:50]}"
        result = memory_service.save_memory(
            content=memory_content,
            category=category,
            tags=tags,
            is_important=True
        )
        return f"已记住: {memory_content}"

    # 检查是否是提醒指令
    reminder = _extract_reminder(text)
    if reminder:
        content, remind_at = reminder
        memory_service.create_reminder(content=content, remind_at=remind_at)
        time_str = f"，时间: {remind_at}" if remind_at else ""
        return f"已创建提醒: {content}{time_str}"

    return None
