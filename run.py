"""
灵眸星视 启动脚本
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from backend.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("  灵眸星视 - AI 视界助理")
    print("=" * 60)
    print(f"  Backend:  http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"  Health:   http://{settings.HOST}:{settings.PORT}/health")
    print("=" * 60)

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
