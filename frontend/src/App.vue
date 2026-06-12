<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <nav class="nav-bar glass-top">
      <div class="nav-content">
        <div class="nav-brand">
          <el-icon class="brand-icon"><Star /></el-icon>
          <span class="brand-text">StarVision</span>
        </div>
        <div class="nav-actions">
          <ThemeSwitcher />
          <SettingsPanel />
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="app-main">
      <div class="main-content">
        <!-- 视频区域 -->
        <section class="video-section fade-in-up">
          <VideoStream />
        </section>

        <!-- 对话区域 -->
        <section class="chat-section fade-in-up delay-1">
          <ChatPanel />
        </section>
      </div>
    </main>

    <!-- 底部状态栏 -->
    <footer class="status-bar glass-base">
      <StatusBar />
      <CostPanel />
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { Star } from '@element-plus/icons-vue'
import VideoStream from './components/VideoStream.vue'
import ChatPanel from './components/ChatPanel.vue'
import StatusBar from './components/StatusBar.vue'
import CostPanel from './components/CostPanel.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import ThemeSwitcher from './components/ThemeSwitcher.vue'
import { wsService } from './services/wsService'
import { useChatStore } from './stores/chatStore'

const chatStore = useChatStore()

// 连接 WebSocket
onMounted(() => {
  wsService.connect()

  // 监听连接状态
  wsService.on('connected', () => {
    chatStore.isConnected = true
  })

  wsService.on('disconnected', () => {
    chatStore.isConnected = false
  })

  // 监听 AI 回复
  wsService.on('ai_response', (data) => {
    chatStore.addMessage(data.text, data.is_user || false)
  })

  // 监听状态更新
  wsService.on('status', (data) => {
    chatStore.setStatus(data.status, data.message)
  })

  // 监听成本更新
  wsService.on('cost_update', (data) => {
    chatStore.updateCost(data)
  })
})

// 断开连接
onUnmounted(() => {
  wsService.disconnect()
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--canvas);
  color: var(--ink);
  overflow: hidden;
}

/* 导航栏 */
.nav-bar {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  padding: 10px 20px;
  border-radius: var(--radius-full);
  background: var(--glass-top);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--shadow-nav);
}

.nav-content {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  font-size: 18px;
  color: var(--accent);
}

.brand-text {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 主内容区 */
.app-main {
  flex: 1;
  padding: 80px 20px 20px;
  overflow: hidden;
}

.main-content {
  display: flex;
  gap: 20px;
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

.video-section {
  flex: 1;
  min-width: 0;
}

.chat-section {
  flex: 1;
  min-width: 0;
}

/* 底部状态栏 */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: var(--glass-base);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 0.5px solid var(--glass-border);
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-bar {
    top: auto;
    bottom: 16px;
    left: 16px;
    right: 16px;
    transform: none;
  }

  .app-main {
    padding: 16px;
    padding-bottom: 80px;
  }

  .main-content {
    flex-direction: column;
  }

  .status-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 50;
  }
}
</style>
