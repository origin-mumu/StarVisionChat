/**
 * 手势识别状态管理
 * 检测逻辑已合并到场景监控（scene_monitor），不再独立发请求
 * 本模块只负责：接收结果、维护锁定状态、显示提示
 */
import { ref } from 'vue'

const DEBOUNCE_MS = 2500

export function useGesture() {
  const isLocked = ref(false)
  const gestureHint = ref('')
  let lastGestureTime = 0

  /** 处理场景监控返回的手势结果 */
  function handleResult(result) {
    if (!result || result === 'none') return

    const now = Date.now()
    if (now - lastGestureTime < DEBOUNCE_MS) return
    lastGestureTime = now

    if (result === 'lock') {
      isLocked.value = true
      gestureHint.value = '👍 场景已锁定'
      setTimeout(() => { gestureHint.value = '' }, 2000)
    } else if (result === 'unlock') {
      isLocked.value = false
      gestureHint.value = '✌️ 智能切换已恢复'
      setTimeout(() => { gestureHint.value = '' }, 2000)
    }
  }

  function cleanup() {}

  return { isLocked, gestureHint, handleResult, cleanup }
}
