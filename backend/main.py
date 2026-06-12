"""
StarVisionChat - AI 视觉对话助手
FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import settings
from .routers import ws_router

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 视觉对话助手 - 能看能听的 AI 对话应用"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ws_router.router, prefix="/api", tags=["websocket"])

# 静态文件服务（前端构建产物）
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")


@app.get("/")
async def root():
    """根路由 - 返回前端页面"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/api/config")
async def get_config():
    """获取公开配置（不包含敏感信息）"""
    return {
        "stt_mode": settings.STT_MODE,
        "tts_mode": settings.TTS_MODE,
        "vision_model": settings.VISION_MODEL,
        "chat_model": settings.CHAT_MODEL,
        "frame_interval": settings.FRAME_INTERVAL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
