/**
 * 会话状态管理
 * 支持多会话：新建、切换、删除
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const SESSIONS_KEY = 'starvisionchat_sessions'
const CURRENT_ID_KEY = 'starvisionchat_current_session'

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return parsed.map(s => ({
        ...s,
        createdAt: new Date(s.createdAt),
        updatedAt: new Date(s.updatedAt),
        messages: (s.messages || []).map(m => ({
          ...m,
          timestamp: new Date(m.timestamp),
        })),
      }))
    }
  } catch { /* ignore */ }
  return []
}

function loadCurrentId() {
  try {
    return localStorage.getItem(CURRENT_ID_KEY) || null
  } catch { return null }
}

export const useSessionStore = defineStore('session', () => {
  const sessions = ref(loadSessions())
  const currentSessionId = ref(loadCurrentId())

  // 如果没有会话，自动创建一个
  if (sessions.value.length === 0) {
    const id = generateId()
    sessions.value.push({
      id,
      title: '新对话',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    })
    currentSessionId.value = id
  }

  // 如果 currentSessionId 指向不存在的会话，重置为第一个
  if (!sessions.value.find(s => s.id === currentSessionId.value)) {
    currentSessionId.value = sessions.value[0].id
  }

  // 持久化
  watch(sessions, (val) => {
    try {
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(val))
    } catch { /* ignore quota */ }
  }, { deep: true })

  watch(currentSessionId, (val) => {
    try {
      localStorage.setItem(CURRENT_ID_KEY, val || '')
    } catch { /* ignore */ }
  })

  // 当前会话
  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value) || null
  )

  // 当前会话的消息
  const currentMessages = computed(() =>
    currentSession.value?.messages || []
  )

  /**
   * 新建会话
   */
  function createSession() {
    const id = generateId()
    sessions.value.unshift({
      id,
      title: '新对话',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    })
    currentSessionId.value = id
    return id
  }

  /**
   * 切换会话
   */
  function switchSession(id) {
    const session = sessions.value.find(s => s.id === id)
    if (session) {
      currentSessionId.value = id
      return session.messages
    }
    return []
  }

  /**
   * 删除会话
   */
  function deleteSession(id) {
    const index = sessions.value.findIndex(s => s.id === id)
    if (index === -1) return

    sessions.value.splice(index, 1)

    // 如果删除的是当前会话，切换到最近的会话
    if (currentSessionId.value === id) {
      if (sessions.value.length > 0) {
        // 切换到列表中最近的会话
        currentSessionId.value = sessions.value[0].id
      } else {
        // 没有会话了，自动创建一个新的
        createSession()
      }
    }
  }

  /**
   * 保存当前会话的消息
   */
  function saveCurrentMessages(messages) {
    const session = currentSession.value
    if (!session) return

    session.messages = messages.map(m => ({
      ...m,
      timestamp: m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp),
    }))
    session.updatedAt = new Date()

    // 自动更新标题：取第一条用户消息的前 20 个字符
    const firstUserMsg = messages.find(m => m.isUser)
    if (firstUserMsg && firstUserMsg.text) {
      session.title = firstUserMsg.text.slice(0, 20) + (firstUserMsg.text.length > 20 ? '...' : '')
    }
  }

  /**
   * 清空当前会话的消息
   */
  function clearCurrentSession() {
    const session = currentSession.value
    if (!session) return
    session.messages = []
    session.title = '新对话'
    session.updatedAt = new Date()
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    currentMessages,
    createSession,
    switchSession,
    deleteSession,
    saveCurrentMessages,
    clearCurrentSession,
  }
})
