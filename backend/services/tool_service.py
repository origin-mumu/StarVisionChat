"""
工具服务
管理工具注册、定义分发、执行调度
"""
import asyncio
from typing import Dict, Any, List
from ..tools import time_tool, calculator_tool, memory_tool, weather_tool


class ToolService:
    def __init__(self):
        # 注册所有工具定义（传给 LLM）
        self.definitions = [
            time_tool.TOOL_DEFINITION,
            calculator_tool.TOOL_DEFINITION,
            weather_tool.TOOL_DEFINITION,
            memory_tool.SAVE_MEMORY_DEF,
            memory_tool.SEARCH_MEMORY_DEF,
            memory_tool.CREATE_REMINDER_DEF,
            memory_tool.LIST_REMINDERS_DEF,
        ]
        # 注册工具执行函数
        self._executors: Dict[str, Any] = {
            "get_current_time": time_tool.execute,
            "calculate": calculator_tool.execute,
            "get_weather": weather_tool.execute,
            "save_memory": memory_tool.execute_save_memory,
            "search_memory": memory_tool.execute_search_memory,
            "create_reminder": memory_tool.execute_create_reminder,
            "list_reminders": memory_tool.execute_list_reminders,
        }
        # 异步工具列表
        self._async_tools = {"get_weather"}

    def get_definitions(self) -> List[Dict]:
        """获取所有工具定义，传给 LLM 的 tools 参数"""
        return self.definitions

    async def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """执行指定工具（自动处理同步/异步）"""
        executor = self._executors.get(name)
        if not executor:
            return f"未知工具: {name}"
        try:
            if name in self._async_tools:
                return await executor(**arguments)
            else:
                return executor(**arguments)
        except Exception as e:
            return f"工具执行失败: {e}"


# 全局实例
tool_service = ToolService()
