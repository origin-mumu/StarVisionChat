/**
 * 对话状态管理
 * 消息存储由 sessionStore 管理，chatStore 负责当前会话的消息操作
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useSessionStore } from './sessionStore'

export const useChatStore = defineStore('chat', () => {
  // 当前消息列表（由 sessionStore 加载）
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

  // 流式消息支持
  const isStreaming = ref(false)
  const streamingText = ref('')
  let streamingMsgId = null

  // 消息变更时自动保存到 sessionStore
  let saveTimer = null
  watch(messages, () => {
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      try {
        const sessionStore = useSessionStore()
        sessionStore.saveCurrentMessages(messages.value)
      } catch { /* sessionStore not ready */ }
    }, 300)
  }, { deep: true })

  /**
   * 加载指定会话的消息
   */
  function loadSession(sessionMessages) {
    messages.value = (sessionMessages || []).map(m => ({
      ...m,
      timestamp: m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp),
    }))
    isStreaming.value = false
    streamingText.value = ''
    streamingMsgId = null
  }

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
   * 开始流式消息（创建 AI 占位消息）
   */
  function startStreamingMessage() {
    isStreaming.value = true
    streamingText.value = ''
    streamingMsgId = Date.now()
    messages.value.push({
      id: streamingMsgId,
      text: '',
      isUser: false,
      timestamp: new Date(),
      isStreaming: true,
    })
  }

  /**
   * 追加流式文本块
   */
  function appendStreamChunk(text) {
    streamingText.value += text
    const msg = messages.value.find(m => m.id === streamingMsgId)
    if (msg) {
      msg.text = streamingText.value
    }
  }

  /**
   * 完成流式消息
   */
  function finishStreamingMessage() {
    isStreaming.value = false
    const msg = messages.value.find(m => m.id === streamingMsgId)
    if (msg) {
      msg.isStreaming = false
    }
    streamingMsgId = null
    streamingText.value = ''
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
   * 清空当前会话消息
   */
  function clearMessages() {
    messages.value = []
    isStreaming.value = false
    streamingText.value = ''
    streamingMsgId = null
    try {
      const sessionStore = useSessionStore()
      sessionStore.clearCurrentSession()
    } catch { /* sessionStore not ready */ }
  }

  /**
   * 获取状态文本
   */
  const statusText = computed(() => {
    const statusMap = {
      'idle': '就绪',
      'listening': '正在聆听...',
      'processing_stt': '正在识别语音...',
      'processing_vision': '正在分析画面...',
      'thinking': '正在思考...',
      'speaking': '正在回复...'
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
    isStreaming,
    streamingText,
    statusText,
    formattedCost,
    loadSession,
    addMessage,
    startStreamingMessage,
    appendStreamChunk,
    finishStreamingMessage,
    setStatus,
    updateCost,
    clearMessages
  }
})
