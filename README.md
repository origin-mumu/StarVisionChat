# 🌟 StarVisionChat - AI 视觉对话助手

一款基于 Web 的 AI 视觉对话应用，能让 AI 实时"看到"摄像头画面、"听到"用户语音，并给予自然流畅的回应。

## ✨ 功能特性

- 📷 **摄像头实时画面** - AI 能看到你展示的内容
- 🎤 **语音交互** - 自然的语音对话体验
- 🤖 **智能视觉问答** - 指着东西问"这是什么"
- 💬 **多轮对话** - 支持上下文记忆
- 💰 **成本可控** - 端云协同，智能降级

## 🏗️ 技术架构

```
前端 (Vue 3 + Vite)
    ↓ WebSocket
后端 (FastAPI + Python)
    ↓
AI 服务 (OpenAI API / 本地 Whisper)
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | FastAPI + WebSocket |
| 视觉理解 | GPT-4o / GPT-4o-mini |
| 语音识别 | Whisper (本地) / Whisper API |
| 语音合成 | Edge-TTS (免费) / OpenAI TTS |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 摄像头和麦克风设备

### 1. 克隆项目

```bash
git clone https://github.com/your-username/StarVisionChat.git
cd StarVisionChat
```

### 2. 安装依赖

**后端依赖：**
```bash
cd backend
pip install -r requirements.txt
```

**前端依赖：**
```bash
cd frontend
npm install
```

### 3. 启动服务

**启动后端（在项目根目录运行）：**
```bash
# 方式 1：使用启动脚本
python run.py

# 方式 2：直接运行 uvicorn
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端（新终端）：**
```bash
cd frontend
npm run dev
```

### 4. 配置 API Key

打开应用后，点击右上角 **⚙️ 设置** 按钮：
- 输入你的 OpenAI API Key
- 选择 API Base URL（支持第三方兼容 API）
- 选择视觉模型和对话模型
- 选择 TTS 语音

配置会自动保存在浏览器本地，下次打开自动加载。

> 💡 **提示**：也支持通过 `.env` 文件配置，但前端设置优先级更高。

### 5. 访问应用

- 前端页面: http://localhost:5173
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 📁 项目结构

```
StarVisionChat/
├── docs/                          # 文档
│   ├── technical-requirements.md  # 技术需求文档
│   └── design-document.md        # 设计文档
├── frontend/                      # 前端 (Vue 3)
│   ├── src/
│   │   ├── components/           # Vue 组件
│   │   ├── composables/          # 组合式函数
│   │   ├── stores/               # Pinia 状态管理
│   │   └── services/             # WebSocket 服务
│   └── package.json
├── backend/                       # 后端 (FastAPI)
│   ├── main.py                   # 入口
│   ├── config.py                 # 配置
│   ├── routers/                  # 路由
│   ├── services/                 # 服务
│   ├── models/                   # 数据模型
│   └── requirements.txt
├── .env.example                   # 环境变量示例
└── README.md
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_BASE_URL` | API 基础 URL | `https://api.openai.com/v1` |
| `VISION_MODEL` | 视觉模型 | `gpt-4o-mini` |
| `CHAT_MODEL` | 对话模型 | `gpt-4o-mini` |
| `STT_MODE` | 语音识别模式 | `local` |
| `TTS_MODE` | 语音合成模式 | `edge` |
| `FRAME_INTERVAL` | 帧采样间隔(秒) | `2.0` |

### 成本控制

- **帧采样**: 仅 1-2 FPS，节省 ~90% 视觉 API 调用
- **本地 Whisper**: STT 完全免费
- **Edge-TTS**: TTS 完全免费
- **模型分级**: 简单问题用 mini 模型

## 📝 开发说明

### 添加新功能

1. 后端服务: 在 `backend/services/` 添加新服务
2. WebSocket 消息: 在 `backend/models/schemas.py` 添加新消息类型
3. 前端组件: 在 `frontend/src/components/` 添加新组件

### WebSocket 消息协议

```javascript
// 客户端 -> 服务端
{ type: "video_frame", data: { image: "base64..." } }
{ type: "audio_chunk", data: { audio: "base64..." } }
{ type: "audio_end" }
{ type: "text_input", data: { text: "..." } }

// 服务端 -> 客户端
{ type: "ai_response", data: { text: "...", is_user: false } }
{ type: "ai_audio", data: { audio: "base64...", format: "mp3" } }
{ type: "status", data: { status: "thinking", message: "..." } }
{ type: "cost_update", data: { vision_calls: 5, ... } }
```

## 📄 文档

- [技术需求文档](docs/technical-requirements.md)
- [设计文档](docs/design-document.md)

## 📊 成本预估

| 场景 | 无优化 | 优化后 |
|------|-------|-------|
| 视觉 API | $18/小时 | $0.5/小时 |
| STT | $3.6/小时 | $0 (本地) |
| TTS | $5.4/小时 | $0 (Edge-TTS) |
| **总计** | **$29/小时** | **$1.3/小时** |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
