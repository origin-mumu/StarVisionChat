"""时间工具"""
from datetime import datetime

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前的日期和时间",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


def execute(**kwargs) -> str:
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return now.strftime(f"%Y年%m月%d日 {weekdays[now.weekday()]} %H:%M")
