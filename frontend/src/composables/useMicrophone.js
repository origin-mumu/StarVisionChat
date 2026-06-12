/**
 * 麦克风组合式函数
 * 处理麦克风采集和 VAD（语音活动检测）
 */
import { ref, onUnmounted } from 'vue'
import { wsService } from '../services/wsService'

export function useMicrophone() {
  const isRecording = ref(false)
  const isSpeaking = ref(false)
  const error = ref(null)

  let mediaStream = null
  let audioContext = null
  let processor = null
  let silenceTimer = null
  let audioChunks = []

  const SILENCE_THRESHOLD = 0.01 // 静音阈值
  const SILENCE_DURATION = 1500  // 静音持续时间（ms）

  /**
   * 开启麦克风
   */
  async function startMicrophone() {
    try {
      error.value = null

      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      })

      // 创建音频上下文
      audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000
      })

      const source = audioContext.createMediaStreamSource(mediaStream)

      // 创建 ScriptProcessor（简单实现，生产环境可用 AudioWorklet）
      processor = audioContext.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)

        // 检测音量
        const volume = Math.max(...inputData.map(Math.abs))

        if (volume > SILENCE_THRESHOLD) {
          // 检测到声音
          if (!isSpeaking.value) {
            isSpeaking.value = true
            audioChunks = []
          }

          // 重置静音计时器
          if (silenceTimer) {
            clearTimeout(silenceTimer)
          }
          silenceTimer = setTimeout(() => {
            // 静音持续时间足够，认为说完
            if (isSpeaking.value) {
              isSpeaking.value = false
              sendAudioData()
            }
          }, SILENCE_DURATION)

          // 收集音频数据
          const pcmData = convertFloat32ToInt16(inputData)
          audioChunks.push(pcmData)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      isRecording.value = true

    } catch (e) {
      console.error('Microphone error:', e)
      error.value = getMicrophoneErrorMessage(e)
    }
  }

  /**
   * 关闭麦克风
   */
  function stopMicrophone() {
    if (silenceTimer) {
      clearTimeout(silenceTimer)
      silenceTimer = null
    }

    if (processor) {
      processor.disconnect()
      processor = null
    }

    if (audioContext) {
      audioContext.close()
      audioContext = null
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop())
      mediaStream = null
    }

    isRecording.value = false
    isSpeaking.value = false
  }

  /**
   * 发送收集的音频数据
   */
  function sendAudioData() {
    if (audioChunks.length === 0) return

    // 合并所有音频片段
    const totalLength = audioChunks.reduce((sum, chunk) => sum + chunk.length, 0)
    const merged = new Int16Array(totalLength)
    let offset = 0
    for (const chunk of audioChunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }

    // 转换为 base64
    const base64 = btoa(String.fromCharCode(...new Uint8Array(merged.buffer)))

    // 发送到服务器
    wsService.sendAudioChunk(base64)
    wsService.sendAudioEnd()

    // 清空缓冲区
    audioChunks = []
  }

  /**
   * Float32 转 Int16
   */
  function convertFloat32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length)
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }
    return int16Array
  }

  /**
   * 获取错误信息
   */
  function getMicrophoneErrorMessage(e) {
    if (e.name === 'NotAllowedError') {
      return '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风'
    } else if (e.name === 'NotFoundError') {
      return '未找到麦克风设备'
    } else if (e.name === 'NotReadableError') {
      return '麦克风被其他应用占用'
    }
    return `麦克风错误: ${e.message}`
  }

  // 组件卸载时清理
  onUnmounted(() => {
    stopMicrophone()
  })

  return {
    isRecording,
    isSpeaking,
    error,
    startMicrophone,
    stopMicrophone
  }
}
