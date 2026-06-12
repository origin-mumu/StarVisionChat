@echo off
echo ========================================
echo   StarVisionChat - AI 视觉对话助手
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/4] 安装后端依赖...
cd backend
pip install -r requirements.txt -q
cd ..

echo [2/4] 安装前端依赖...
cd frontend
call npm install --silent
cd ..

echo [3/4] 检查环境配置...
if not exist .env (
    echo [提示] 未找到 .env 文件，正在从模板创建...
    copy .env.example .env
    echo [提示] 请编辑 .env 文件配置你的 API Key
)

echo [4/4] 启动服务...
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

REM 启动后端（新窗口）
start "StarVisionChat Backend" cmd /k "cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
cd frontend
call npm run dev
