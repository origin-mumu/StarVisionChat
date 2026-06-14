"""记忆工具 — 供 LLM 调用"""
from ..services import memory_service

SAVE_MEMORY_DEF = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": "保存用户的重要信息到长期记忆。当用户说'帮我记一下'、'记住'、'别忘了'等意图时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "要记忆的内容"
                },
                "category": {
                    "type": "string",
                    "enum": ["preference", "fact", "event", "todo"],
                    "description": "分类: preference=偏好, fact=事实, event=事件, todo=待办"
                },
                "is_important": {
                    "type": "boolean",
                    "description": "是否重要/需要置顶"
                }
            },
            "required": ["content", "category"]
        }
    }
}

SEARCH_MEMORY_DEF = {
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": "搜索用户的记忆，查找之前保存的信息",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["keyword"]
        }
    }
}

CREATE_REMINDER_DEF = {
    "type": "function",
    "function": {
        "name": "create_reminder",
        "description": "创建待办提醒。当用户说'提醒我'、'别忘了'、'明天有XX'等包含时间的意图时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "提醒内容"
                },
                "remind_at": {
                    "type": "string",
                    "description": "提醒时间，格式 'YYYY-MM-DD HH:MM'"
                }
            },
            "required": ["content"]
        }
    }
}

LIST_REMINDERS_DEF = {
    "type": "function",
    "function": {
        "name": "list_reminders",
        "description": "查看待办提醒列表",
        "parameters": {
            "type": "object",
            "properties": {
                "show_done": {
                    "type": "boolean",
                    "description": "是否显示已完成的提醒，默认只显示未完成"
                }
            },
            "required": []
        }
    }
}


def execute_save_memory(content: str, category: str = "fact", is_important: bool = False, **kwargs) -> str:
    result = memory_service.save_memory(content, category=category, is_important=is_important)
    return f"已记住: {result['content']}"


def execute_search_memory(keyword: str, **kwargs) -> str:
    results = memory_service.search_memories(keyword)
    if not results:
        return f"没有找到关于'{keyword}'的记忆"
    items = [f"- {m['content']} ({m['category']})" for m in results]
    return "找到以下记忆:\n" + "\n".join(items)


def execute_create_reminder(content: str, remind_at: str = None, **kwargs) -> str:
    result = memory_service.create_reminder(content, remind_at=remind_at)
    time_str = f"，时间: {remind_at}" if remind_at else ""
    return f"已创建提醒: {result['content']}{time_str}"


def execute_list_reminders(show_done: bool = False, **kwargs) -> str:
    is_done = None if show_done else False
    reminders = memory_service.get_reminders(is_done=is_done)
    if not reminders:
        return "暂无待办提醒"
    items = []
    for r in reminders:
        status = "[x]" if r["is_done"] else "[ ]"
        time_str = f" ({r['remind_at']})" if r["remind_at"] else ""
        items.append(f"{status} {r['content']}{time_str}")
    return "待办提醒:\n" + "\n".join(items)
