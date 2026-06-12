<template>
  <div class="status-container">
    <!-- 状态指示器 -->
    <div class="status-indicator">
      <span :class="['status-dot', status]"></span>
      <span class="text-body-small">{{ statusText }}</span>
    </div>

    <!-- 状态消息 -->
    <Transition name="ui-fade">
      <span v-if="statusMessage" class="status-message text-caption">
        {{ statusMessage }}
      </span>
    </Transition>

    <!-- 连接状态 -->
    <div class="connection-status">
      <span :class="['status-dot', isConnected ? 'active' : 'error']"></span>
      <span class="text-caption">{{ isConnected ? '已连接' : '未连接' }}</span>
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../stores/chatStore'
import { storeToRefs } from 'pinia'

const chatStore = useChatStore()
const { status, statusMessage, statusText, isConnected } = storeToRefs(chatStore)
</script>

<style scoped>
.status-container {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ink-muted);
  transition: all var(--transition);
}

.status-dot.active {
  background: #4CAF50;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.5);
}

.status-dot.listening {
  background: #FF9800;
  box-shadow: 0 0 8px rgba(255, 152, 0, 0.5);
}

.status-dot.processing_stt {
  background: #2196F3;
  box-shadow: 0 0 8px rgba(33, 150, 243, 0.5);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-dot.processing_vision {
  background: #9C27B0;
  box-shadow: 0 0 8px rgba(156, 39, 176, 0.5);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-dot.thinking {
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent-soft);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-dot.speaking {
  background: #00BCD4;
  box-shadow: 0 0 8px rgba(0, 188, 212, 0.5);
}

.status-dot.error {
  background: #F44336;
  box-shadow: 0 0 8px rgba(244, 67, 54, 0.5);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-message {
  color: var(--ink-muted);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
