<template>
  <div class="chat-container glass-card">
    <!-- 对话头部 -->
    <div class="chat-header">
      <div class="header-left">
        <span class="text-h3">对话</span>
        <span class="tag">{{ messages.length }} 条消息</span>
      </div>
      <button class="btn-ghost" @click="clearMessages">
        <el-icon><Delete /></el-icon>
        清空
      </button>
    </div>

    <!-- 消息列表 -->
    <div class="messages-wrapper" ref="messagesRef">
      <div class="messages-list">
        <div
          v-for="(msg, index) in messages"
          :key="msg.id"
          :class="['message-item', { 'user-message': msg.isUser }]"
          :style="{ animationDelay: `${index * 40}ms` }"
          class="fade-in-up"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.isUser"><User /></el-icon>
            <el-icon v-else><Star /></el-icon>
          </div>
          <div class="message-bubble" :class="msg.isUser ? 'user' : 'assistant'">
            <div class="message-text">{{ msg.text }}</div>
            <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-icon">
            <el-icon :size="32"><ChatDotRound /></el-icon>
          </div>
          <p class="text-h3">开始对话</p>
          <p class="text-caption">开启摄像头和麦克风，或在下方输入文字</p>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-wrapper">
        <input
          v-model="inputText"
          class="input-field"
          placeholder="输入文字测试..."
          @keyup.enter="sendText"
          :disabled="!isConnected"
        />
        <button
          class="btn-primary"
          @click="sendText"
          :disabled="!inputText.trim() || !isConnected"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { Delete, User, Star, ChatDotRound, Promotion } from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chatStore'
import { wsService } from '../services/wsService'
import { storeToRefs } from 'pinia'

const chatStore = useChatStore()
const { messages, isConnected } = storeToRefs(chatStore)

const inputText = ref('')
const messagesRef = ref(null)

function sendText() {
  const text = inputText.value.trim()
  if (!text) return

  // 显示用户消息
  chatStore.addMessage(text, true)

  // 发送到服务器
  wsService.sendTextInput(text)

  inputText.value = ''
}

function clearMessages() {
  chatStore.clearMessages()
}

function formatTime(date) {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 自动滚动到底部
watch(messages, async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}, { deep: true })
</script>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

/* 头部 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 0.5px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 消息列表 */
.messages-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.message-item {
  display: flex;
  gap: var(--space-3);
  max-width: 85%;
}

.user-message {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--glass-mid);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--accent);
}

.user-message .message-avatar {
  background: var(--accent-soft);
}

.message-bubble {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  word-break: break-word;
}

.message-bubble.user {
  background: var(--accent);
  color: white;
  border-bottom-right-radius: var(--radius-sm);
}

.message-bubble.assistant {
  background: var(--glass-mid);
  color: var(--ink);
  border-bottom-left-radius: var(--radius-sm);
}

.message-text {
  line-height: 1.6;
}

.message-time {
  font-size: var(--text-caption);
  color: var(--ink-muted);
  margin-top: var(--space-1);
}

.user-message .message-time {
  color: rgba(255, 255, 255, 0.7);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) 0;
  gap: var(--space-3);
  color: var(--ink-muted);
}

.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-mid);
  border-radius: var(--radius-xl);
  color: var(--ink-muted);
}

/* 输入区域 */
.input-area {
  padding: var(--space-4);
  border-top: 0.5px solid var(--border);
}

.input-wrapper {
  display: flex;
  gap: var(--space-3);
}

.input-wrapper .input-field {
  flex: 1;
}

.input-wrapper .btn-primary {
  flex-shrink: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .message-item {
    max-width: 95%;
  }
}
</style>
