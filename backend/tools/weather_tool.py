"""天气查询工具"""
import httpx

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的当前天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如 '北京'、'上海'"
                }
            },
            "required": ["city"]
        }
    }
}


async def execute(city: str, **kwargs) -> str:
    """使用 wttr.in 免费天气 API"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=zh"
            )
            if resp.status_code == 200:
                data = resp.text.strip()
                return f"{city}天气: {data}"
            return f"无法获取{city}的天气信息"
    except Exception as e:
        return f"天气查询失败: {e}"
