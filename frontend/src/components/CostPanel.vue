<template>
  <div class="cost-container">
    <button class="btn-ghost cost-button" @click="showDetails = !showDetails">
      <el-icon><Coin /></el-icon>
      <span class="text-body-small">{{ formattedCost }}</span>
    </button>

    <!-- 成本详情弹窗 -->
    <Transition name="ui-fade">
      <div v-if="showDetails" class="cost-details glass-mid">
        <div class="details-header">
          <span class="text-h3">成本统计</span>
          <button class="btn-icon" @click="showDetails = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <div class="cost-items">
          <div class="cost-item">
            <div class="item-left">
              <el-icon><View /></el-icon>
              <span class="text-body-small">视觉调用</span>
            </div>
            <span class="text-body-small">{{ costData.vision_calls }} 次</span>
          </div>

          <div class="cost-item">
            <div class="item-left">
              <el-icon><Microphone /></el-icon>
              <span class="text-body-small">语音识别</span>
            </div>
            <span class="text-body-small">{{ costData.stt_calls }} 次</span>
          </div>

          <div class="cost-item">
            <div class="item-left">
              <el-icon><ChatLineRound /></el-icon>
              <span class="text-body-small">LLM Tokens</span>
            </div>
            <span class="text-body-small">{{ costData.llm_tokens }}</span>
          </div>

          <div class="cost-item">
            <div class="item-left">
              <el-icon><Headset /></el-icon>
              <span class="text-body-small">TTS 字符</span>
            </div>
            <span class="text-body-small">{{ costData.tts_chars }}</span>
          </div>
        </div>

        <div class="cost-total">
          <span class="text-body-small">预估费用</span>
          <span class="total-amount text-h3">{{ formattedCost }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Coin, Close, View, Microphone, ChatLineRound, Headset } from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chatStore'
import { storeToRefs } from 'pinia'

const chatStore = useChatStore()
const { costData, formattedCost } = storeToRefs(chatStore)

const showDetails = ref(false)
</script>

<style scoped>
.cost-container {
  position: relative;
}

.cost-button {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--warm);
}

/* 详情弹窗 */
.cost-details {
  position: absolute;
  bottom: calc(100% + 12px);
  right: 0;
  width: 280px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--glass-mid);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--shadow-card);
  z-index: 100;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 0.5px solid var(--border);
}

.cost-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--ink-soft);
}

.cost-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
}

.total-amount {
  color: var(--accent);
  font-weight: 700;
}
</style>
