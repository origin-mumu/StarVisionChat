/**
 * 摄像头组合式函数
 * 处理摄像头采集，支持手动捕获当前帧
 */
import { ref, onUnmounted } from 'vue'

export function useCamera() {
  const videoRef = ref(null)
  const canvasRef = ref(null)
  const isStreaming = ref(false)
  const error = ref(null)

  let stream = null

  /**
   * 开启摄像头
   */
  async function startCamera() {
    try {
      error.value = null

      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      })

      if (videoRef.value) {
        videoRef.value.srcObject = stream
        await videoRef.value.play()
      }

      isStreaming.value = true

    } catch (e) {
      console.error('Camera error:', e)
      error.value = getCameraErrorMessage(e)
    }
  }

  /**
   * 关闭摄像头
   */
  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      stream = null
    }

    if (videoRef.value) {
      videoRef.value.srcObject = null
    }

    isStreaming.value = false
  }

  /**
   * 捕获当前帧，返回 base64（不含 data:image 前缀）
   */
  function captureFrame() {
    if (!videoRef.value || !isStreaming.value) return null

    const canvas = document.createElement('canvas')
    const video = videoRef.value

    const maxWidth = 640
    const scale = Math.min(1, maxWidth / video.videoWidth)
    canvas.width = video.videoWidth * scale
    canvas.height = video.videoHeight * scale

    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    const imageBase64 = canvas.toDataURL('image/jpeg', 0.6)
      .replace('data:image/jpeg;base64,', '')

    return imageBase64
  }

  /**
   * 获取错误信息
   */
  function getCameraErrorMessage(e) {
    if (e.name === 'NotAllowedError') {
      return '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头'
    } else if (e.name === 'NotFoundError') {
      return '未找到摄像头设备'
    } else if (e.name === 'NotReadableError') {
      return '摄像头被其他应用占用'
    }
    return `摄像头错误: ${e.message}`
  }

  // 组件卸载时清理
  onUnmounted(() => {
    stopCamera()
  })

  return {
    videoRef,
    canvasRef,
    isStreaming,
    error,
    startCamera,
    stopCamera,
    captureFrame
  }
}
