# 🌟 灵眸星视 — 一个 AI 视界助理

> 像人一样用眼睛看世界，用耳朵听声音，用心记住你。融合视觉感知、语音交互与持久记忆的多模态 AI 视界助理。

![Vue 3](https://img.shields.io/badge/Vue-3.5-4FC08D?logo=vuedotjs)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![WebSocket](https://img.shields.io/badge/WebSocket-实时通信-ff69b4)
![Pinia](https://img.shields.io/badge/Pinia-2.x-ffd859)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)

---

## 🎬 Demo 视频

> **Demo 演示视频**：[点击观看](https://www.bilibili.com/video/BV1sSJA6NEHa/)

---

## 📋 设计与实现报告

详见 [docs/design-report.md](docs/design-report.md)，包含：

- 业务场景与目标用户分析
- 用户故事计划 vs 实际实现对照
- 成本控制策略与效果对比
- 技术架构与关键决策
- WebSocket 消息协议完整文档

---

## ✨ 功能特性

| 模块                | 说明                                                      |
| ------------------- | --------------------------------------------------------- |
| 📷 **实时视觉感知** | 摄像头捕捉 + AI 即时理解画面，支持手机远程摄像头          |
| 🎙️ **语音自然对话** | 语音输入 + TTS 播报，支持 MiMo / Qwen 双引擎              |
| 🔄 **连续对话模式** | AI 说完自动开始下一轮录音，无需反复点击                   |
| 🧠 **场景智能识别** | 6 大内置场景 + 自定义场景，关键词/视觉双通道自动切换      |
| 👍 **手势锁定控制** | 竖大拇指锁定场景，剪刀手解锁，AI 视觉识别手势             |
| 📝 **持久记忆系统** | AI 记住重要信息与待办，跨会话持久保存                     |
| 📊 **用量一目了然** | API 调用、Token 消耗实时透明                              |
| 🎨 **6 套主题**     | 暖白 · 纯灰 · 深空 · 薄荷 · 浅海 · 裸粉，粒子系统实时响应 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────┐
│  前端 (Vue 3 + Vite + Pinia + vue-router)   │
│  3D 粒子动画 · 摄像头 · 麦克风 · TTS        │
└──────────────────┬──────────────────────────┘
                   │ WebSocket (JSON + base64)
┌──────────────────▼──────────────────────────┐
│  后端 (FastAPI + Python)                     │
│  WebSocket 路由 · 会话管理 · 工具调用框架     │
└──────────────────┬──────────────────────────┘
                   │ OpenAI 兼容 API
┌──────────────────▼──────────────────────────┐
│  AI 服务                                     │
│  MiMo (小米) / Qwen-Omni (阿里)             │
│  视觉理解 · 语音识别 · 语音合成 · 对话       │
└─────────────────────────────────────────────┘
```

---

## 📦 依赖清单与原创说明

### 前端依赖 (`frontend/package.json`)

| 依赖                      | 版本     | 用途             | 类型     |
| ------------------------- | -------- | ---------------- | -------- |
| `vue`                     | ^3.5.13  | 前端框架         | 第三方   |
| `vue-router`              | ^4.6.4   | 路由管理         | 第三方   |
| `pinia`                   | ^2.3.0   | 状态管理         | 第三方   |
| `element-plus`            | ^2.9.1   | UI 组件库        | 第三方   |
| `marked`                  | ^18.0.5  | Markdown 渲染    | 第三方   |
| `highlight.js`            | ^11.11.1 | 代码语法高亮     | 第三方   |
| `@mediapipe/tasks-vision` | ^0.10.35 | 手势识别（备用） | 第三方   |
| `vite`                    | ^6.0.5   | 构建工具         | 开发依赖 |
| `@vitejs/plugin-vue`      | ^5.2.1   | Vue 插件         | 开发依赖 |

### 后端依赖 (`backend/requirements.txt`)

| 依赖            | 版本    | 用途                | 类型   |
| --------------- | ------- | ------------------- | ------ |
| `fastapi`       | 0.115.6 | Web 框架            | 第三方 |
| `uvicorn`       | 0.34.0  | ASGI 服务器         | 第三方 |
| `websockets`    | 14.1    | WebSocket 支持      | 第三方 |
| `httpx`         | 0.28.1  | HTTP 客户端         | 第三方 |
| `openai`        | 1.58.1  | OpenAI 兼容 API SDK | 第三方 |
| `pydub`         | 0.25.1  | 音频处理            | 第三方 |
| `ffmpeg-python` | 0.2.0   | 音视频转码          | 第三方 |
| `Pillow`        | 11.1.0  | 图像处理            | 第三方 |
| `pydantic`      | 2.10.4  | 数据模型校验        | 第三方 |
| `python-dotenv` | 1.0.1   | 环境变量管理        | 第三方 |
| `numpy`         | 2.2.1   | 数值计算            | 第三方 |

### 自研功能部分

以下功能为**完全原创开发**，未使用第三方库的核心逻辑：

| 自研模块                | 文件                                    | 说明                                                    |
| ----------------------- | --------------------------------------- | ------------------------------------------------------- |
| **3D 粒子球体动画**     | `ImmersiveChat.vue` (Canvas)            | 原生 Canvas 实现 300 粒子球体旋转、音频响应、状态联动   |
| **液态光球 + 声波动画** | `ImmersiveChat.vue` (Wave)              | 原生 Canvas 实现光球到声波的形态过渡动画                |
| **场景智能切换系统**    | `sceneStore.js` + `ws_router.py`        | 关键词匹配 + AI 视觉双通道场景检测                      |
| **手势锁定控制系统**    | `useGesture.js` + `ws_router.py`        | AI 视觉识别手势，根据锁定状态动态切换 prompt            |
| **连续对话系统**        | `ImmersiveChat.vue`                     | AI 说完自动触发录音，实现语音循环对话                   |
| **持久记忆系统**        | `memory_service.py` + `MemoryPanel.vue` | SQLite 存储 + 关键词自动提取 + Function Calling         |
| **工具调用框架**        | `tool_service.py` + `tools/`            | 自研 Function Calling 框架，支持时间/计算/天气/记忆工具 |
| **多会话管理**          | `sessionStore.js`                       | localStorage 持久化的多会话切换                         |
| **WebRTC 远程摄像头**   | `ws_router.py` + `RemoteCamera.vue`     | WebSocket 信令中继 + P2P 视频流                         |
| **双引擎适配层**        | `ws_router.py`                          | MiMo / Qwen-Omni 双引擎统一 WebSocket 接口              |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 摄像头和麦克风设备

### 1. 克隆项目

```bash
git clone https://github.com/origin-mumu/StarVisionChat.git
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

| 地址                         | 说明     |
| ---------------------------- | -------- |
| http://localhost:5173        | 前端应用 |
| http://localhost:8000/docs   | API 文档 |
| http://localhost:8000/health | 健康检查 |

---

## 📁 项目结构

```
StarVisionChat/
├── frontend/                          # 前端 (Vue 3)
│   ├── src/
│   │   ├── components/                # 页面 & UI 组件
│   │   │   ├── CoverPage.vue          #   封面宣传页（粒子动画 + 功能卡片）
│   │   │   ├── ConfigPage.vue         #   配置页（MiMo/Qwen 模型选择）
│   │   │   ├── ImmersiveChat.vue      #   核心对话页（3D粒子 + 语音 + 视觉）
│   │   │   ├── SettingsPanel.vue      #   运行时设置浮窗
│   │   │   └── MemoryPanel.vue        #   记忆/待办管理面板
│   │   ├── views/
│   │   │   └── RemoteCamera.vue       #   手机端远程摄像头页面
│   │   ├── stores/                    # Pinia 状态管理
│   │   │   ├── chatStore.js           #   对话消息 & 费用统计
│   │   │   ├── sceneStore.js          #   6大场景 + 自定义场景 + 自动切换
│   │   │   ├── sessionStore.js        #   多会话持久化
│   │   │   └── themeStore.js          #   6套主题管理
│   │   ├── composables/               # 组合式函数
│   │   │   ├── useCamera.js           #   摄像头控制 & 帧捕获
│   │   │   ├── useGesture.js          #   手势锁定状态管理
│   │   │   ├── useMicrophone.js       #   麦克风 & VAD
│   │   │   └── useTTS.js              #   浏览器 TTS
│   │   ├── services/
│   │   │   └── wsService.js           #   WebSocket 单例客户端
│   │   ├── router/index.js            #   路由配置
│   │   └── styles/                    # 主题 tokens & 全局样式
│   ├── package.json
│   └── vite.config.js
├── backend/                           # 后端 (FastAPI)
│   ├── main.py                        #   应用入口
│   ├── config.py                      #   双引擎配置管理
│   ├── routers/
│   │   ├── ws_router.py               #   WebSocket 路由（对话/视觉/场景/手势/信令）
│   │   └── memory_router.py           #   记忆 REST API
│   ├── services/
│   │   ├── llm_service.py             #   MiMo LLM + Function Calling
│   │   ├── qwen_service.py            #   Qwen-Omni Realtime + HTTP
│   │   ├── stt_service.py             #   语音识别 (MiMo ASR)
│   │   ├── tts_service.py             #   语音合成 (MiMo TTS)
│   │   ├── vision_service.py          #   视觉理解
│   │   ├── memory_service.py          #   SQLite 记忆存储
│   │   ├── memory_interceptor.py      #   关键词记忆自动提取
│   │   ├── tool_service.py            #   工具调用框架
│   │   └── session_manager.py         #   会话状态管理
│   ├── tools/                         #   内置工具（时间/计算/天气/记忆）
│   ├── models/schemas.py              #   数据模型定义
│   └── requirements.txt
├── .env.example                       # 环境变量示例
└── README.md
```

---

## 🔧 配置说明

### 环境变量 (`.env`)

| 变量名              | 说明               | 默认值                                    |
| ------------------- | ------------------ | ----------------------------------------- |
| `MIMO_API_KEY`      | MiMo API Key       | —                                         |
| `MIMO_BASE_URL`     | MiMo API 地址      | `https://token-plan-cn.xiaomimimo.com/v1` |
| `CHAT_MODEL`        | 对话模型           | `mimo-v2.5`                               |
| `ASR_MODEL`         | 语音识别模型       | `mimo-v2.5-asr`                           |
| `TTS_MODEL`         | 语音合成模型       | `mimo-v2.5-tts`                           |
| `TTS_VOICE`         | TTS 音色           | `mimo_default`                            |
| `FRAME_INTERVAL`    | 视觉帧采样间隔(秒) | `2.0`                                     |
| `MAX_HISTORY_TURNS` | 最大对话轮数       | `10`                                      |

> 前端配置页设置的参数优先级高于 `.env`。

---

## 📡 WebSocket 消息协议

### 客户端 → 服务端

| 类型             | 数据                                          | 说明                 |
| ---------------- | --------------------------------------------- | -------------------- |
| `video_frame`    | `{ image }`                                   | 摄像头帧             |
| `audio_chunk`    | `{ audio }`                                   | 音频数据块 (MiMo)    |
| `audio_end`      | `{ image? }`                                  | 录音结束 (MiMo)      |
| `audio_stream`   | `{ audio }`                                   | 实时 PCM 音频 (Qwen) |
| `audio_end_qwen` | —                                             | 录音结束 (Qwen)      |
| `text_input`     | `{ text, image? }`                            | 文字消息             |
| `scene_monitor`  | `{ image, scenes, current_scene, is_locked }` | 场景+手势检测        |
| `config_update`  | `{ ... }`                                     | 运行时配置更新       |
| `scene_update`   | `{ system_prompt }`                           | 场景切换             |

### 服务端 → 客户端

| 类型               | 数据                  | 说明                       |
| ------------------ | --------------------- | -------------------------- |
| `ai_response`      | `{ text, is_user }`   | AI/用户文本                |
| `ai_audio`         | `{ audio, format }`   | TTS 音频 (MiMo)            |
| `status`           | `{ status, message }` | 状态更新                   |
| `scene_detected`   | `{ scene, name }`     | 场景切换建议               |
| `gesture_result`   | `{ result }`          | 手势识别结果 (lock/unlock) |
| `memory_saved`     | `{ message }`         | 记忆保存通知               |
| `qwen_text_delta`  | `{ text }`            | Qwen 流式文本              |
| `qwen_audio_delta` | `{ audio }`           | Qwen 流式音频              |
| `qwen_transcript`  | `{ text }`            | Qwen 语音转录              |
| `cost_update`      | `{ ... }`             | 费用统计                   |

---

## 📄 许可证

MIT License
