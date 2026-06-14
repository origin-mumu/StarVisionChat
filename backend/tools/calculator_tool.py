"""数学计算工具"""
import math

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "执行数学计算，支持加减乘除、幂运算、三角函数等",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2+3*4', 'sqrt(16)', 'sin(3.14/2)'"
                }
            },
            "required": ["expression"]
        }
    }
}

SAFE_NAMES = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sqrt": math.sqrt, "pow": pow, "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "ceil": math.ceil, "floor": math.floor,
}


def execute(expression: str, **kwargs) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, SAFE_NAMES)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"
