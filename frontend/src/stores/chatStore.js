/**
 * 对话状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useChatStore = defineStore('chat', () => {
  // 消息列表
  const messages = ref([])

  // 当前状态
  const status = ref('idle')
  const statusMessage = ref('')

  // 成本数据
  const costData = ref({
    vision_calls: 0,
    stt_calls: 0,
    llm_tokens: 0,
    tts_chars: 0,
    estimated_cost: 0
  })

  // 连接状态
  const isConnected = ref(false)

  /**
   * 添加消息
   */
  function addMessage(text, isUser = false) {
    messages.value.push({
      id: Date.now(),
      text,
      isUser,
      timestamp: new Date()
    })

    // 保持消息列表在合理范围内
    if (messages.value.length > 100) {
      messages.value = messages.value.slice(-50)
    }
  }

  /**
   * 更新状态
   */
  function setStatus(newStatus, message = '') {
    status.value = newStatus
    statusMessage.value = message
  }

  /**
   * 更新成本数据
   */
  function updateCost(data) {
    costData.value = { ...costData.value, ...data }
  }

  /**
   * 清空消息
   */
  function clearMessages() {
    messages.value = []
  }

  /**
   * 获取状态文本
   */
  const statusText = computed(() => {
    const statusMap = {
      'idle': '🟢 就绪',
      'listening': '🎤 正在聆听...',
      'processing_stt': '✏️ 正在识别语音...',
      'processing_vision': '👁️ 正在分析画面...',
      'thinking': '🤔 正在思考...',
      'speaking': '💬 正在回复...'
    }
    return statusMap[status.value] || status.value
  })

  /**
   * 格式化成本
   */
  const formattedCost = computed(() => {
    return `$${costData.value.estimated_cost.toFixed(4)}`
  })

  return {
    messages,
    status,
    statusMessage,
    costData,
    isConnected,
    statusText,
    formattedCost,
    addMessage,
    setStatus,
    updateCost,
    clearMessages
  }
})
