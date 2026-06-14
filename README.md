# 🌟 StarVisionChat — 让 AI 拥有眼睛、耳朵和记忆

> 像人一样看世界、听声音、记住你。融合视觉感知、语音交互与持久记忆的多模态 AI 对话助手。

![技术栈](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs) ![技术栈](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) ![技术栈](https://img.shields.io/badge/WebSocket-实时通信-ff69b4) ![技术栈](https://img.shields.io/badge/Pinia-2.x-ffd859)

---

## ✨ 功能特性

| 模块 | 说明 |
|------|------|
| 📷 **实时视觉感知** | 摄像头捕捉 + AI 即时理解画面，所见即所得 |
| 🎙️ **语音自然对话** | 语音输入 + TTS 播报，无需打字自由交流 |
| 🧠 **场景智能识别** | 多场景自动切换，从做饭助手到学习陪伴 |
| 🔌 **多模型自由切换** | MiMo / Qwen-Omni 双引擎，按需选择 |
| 📝 **持久记忆系统** | AI 记住重要信息与上下文，越用越懂你 |
| 📊 **用量一目了然** | API 调用、Token 消耗、费用实时透明 |
| 🎨 **6 套主题** | 暖白 · 纯灰 · 深空 · 薄荷 · 浅海 · 裸粉 |

---

## 🏗️ 技术架构

```
前端 (Vue 3 + Vite + Pinia + vue-router)
    ↓ WebSocket
后端 (FastAPI + Python)
    ↓
AI 服务 (MiMo / Qwen-Omni / Whisper / Edge-TTS)
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite |
| UI 组件库 | Element Plus |
| 状态管理 | Pinia |
| 路由 | vue-router 4 (Hash 模式) |
| 通信 | WebSocket 实时双向 |
| 后端框架 | FastAPI |
| 视觉理解 | GPT-4o / MiMo / Qwen-Omni |
| 语音识别 | Whisper (本地) / MiMo ASR |
| 语音合成 | Edge-TTS / MiMo TTS / Qwen TTS |
| 数据存储 | SQLite (记忆) + localStorage (配置) |

---

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

**后端：**
```bash
cd backend
pip install -r requirements.txt
```

**前端：**
```bash
cd frontend
npm install
```

### 3. 启动服务

**启动后端（项目根目录）：**
```bash
python run.py
# 或
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端（新终端）：**
```bash
cd frontend
npm run dev
```

### 4. 配置

打开 http://localhost:5173 → 封面页 → 点击"开始探索"进入配置页：

- **模型选择**：MiMo 或 Qwen-Omni
- **API Key**：填入对应模型的 API Key
- **模型参数**：选择视觉/对话/语音合成模型

配置保存在浏览器本地，下次自动加载。也可通过 `.env` 预设。

### 5. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端应用 |
| http://localhost:8000/docs | API 文档 |
| http://localhost:8000/health | 健康检查 |

---

## 📁 项目结构

```
StarVisionChat/
├── frontend/                         # 前端 (Vue 3)
│   ├── src/
│   │   ├── components/              # 页面 & UI 组件
│   │   │   ├── CoverPage.vue        #   封面宣传页
│   │   │   ├── ConfigPage.vue       #   配置页（模型选择）
│   │   │   ├── ImmersiveChat.vue    #   核心对话页
│   │   │   ├── SettingsPanel.vue    #   设置浮窗
│   │   │   ├── MemoryPanel.vue      #   记忆管理面板
│   │   │   ├── CostPanel.vue        #   成本统计
│   │   │   ├── StatusBar.vue        #   状态栏
│   │   │   └── ThemeSwitcher.vue    #   主题切换
│   │   ├── router/                  # 路由配置
│   │   ├── stores/                  # Pinia 状态
│   │   │   ├── chatStore.js         #   对话状态
│   │   │   ├── themeStore.js        #   主题状态
│   │   │   ├── sessionStore.js      #   会话管理
│   │   │   └── sceneStore.js        #   场景管理
│   │   ├── composables/             # 组合式函数
│   │   │   ├── useCamera.js         #   摄像头控制
│   │   │   ├── useMicrophone.js     #   麦克风控制
│   │   │   └── useTTS.js            #   语音合成
│   │   ├── services/                # WebSocket 服务
│   │   └── styles/                  # 主题 tokens & 全局样式
│   └── package.json
├── backend/                          # 后端 (FastAPI)
│   ├── main.py                      # 应用入口
│   ├── config.py                    # 配置管理
│   ├── routers/
│   │   ├── ws_router.py             #   WebSocket 路由
│   │   └── memory_router.py         #   记忆 REST API
│   ├── services/
│   │   ├── llm_service.py           #   LLM 调用封装
│   │   ├── qwen_service.py          #   Qwen-Omni 服务
│   │   ├── memory_service.py        #   记忆存储服务
│   │   ├── memory_interceptor.py    #   记忆自动提取
│   │   ├── tool_service.py          #   工具调用框架
│   │   └── session_manager.py       #   会话管理
│   ├── tools/                       # 内置工具集
│   ├── models/                      # 数据模型
│   └── requirements.txt
├── docs/                            # 文档
├── .env.example                     # 环境变量示例
└── README.md
```

---

## 🔧 配置说明

### 环境变量 (`.env`)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI / 兼容 API Key | — |
| `OPENAI_BASE_URL` | API 基础地址 | `https://api.openai.com/v1` |
| `VISION_MODEL` | 视觉模型 | `gpt-4o-mini` |
| `CHAT_MODEL` | 对话模型 | `gpt-4o-mini` |
| `STT_MODE` | 语音识别模式 | `local` |
| `TTS_MODE` | 语音合成模式 | `edge` |

> 前端配置页设置的参数优先级高于 `.env`。

---

## 📡 WebSocket 消息协议

```typescript
// 客户端 → 服务端
{ type: "video_frame",       data: { image: "base64..." } }
{ type: "audio_chunk",       data: { audio: "base64..." } }
{ type: "audio_end" }
{ type: "text_input",        data: { text: "..." } }
{ type: "config_update",     data: { api_key, model_provider, ... } }
{ type: "set_scene",         data: { scene_id: "..." } }

// 服务端 → 客户端
{ type: "ai_response",       data: { text: "...", is_user: false } }
{ type: "ai_audio",          data: { audio: "base64...", format: "mp3" } }
{ type: "status",            data: { status: "thinking", message: "..." } }
{ type: "cost_update",       data: { vision_calls, stt_calls, tokens, ... } }
{ type: "memory_update",     data: { action: "added", memory: {...} } }
{ type: "scene_detect",      data: { scene: {...} } }
```

---

## 📊 成本预估

| 场景 | 无优化 | 优化后 (帧采样 + 本地 STT/TTS) |
|------|--------|-------------------------------|
| 视觉 API | ~$18/小时 | ~$0.5/小时 |
| 语音识别 | ~$3.6/小时 | $0 (本地 Whisper) |
| 语音合成 | ~$5.4/小时 | $0 (Edge-TTS) |
| **总计** | **~$29/小时** | **~$1.3/小时** |

---

## 📝 开发

### 添加新功能

1. 后端服务：`backend/services/` 添加服务类
2. 路由：`backend/routers/` 添加 REST / WebSocket 端点
3. 前端组件：`frontend/src/components/` 添加 `.vue` 组件
4. 状态管理：`frontend/src/stores/` 添加 Pinia store
5. 工具：`backend/tools/` 添加工具函数

### 路由结构

```
/        → CoverPage   (封面)
/config  → ConfigPage  (配置)
/chat    → ImmersiveChat (对话)
```

已配置用户自动从 `/` 跳转至 `/chat`。

---

## 🎬 Demo 视频

> [待上传至 Bilibili / 云盘，放链接]

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
