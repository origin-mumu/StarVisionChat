/**
 * 摄像头组合式函数
 * 处理摄像头采集和帧采样
 */
import { ref, onUnmounted } from 'vue'
import { wsService } from '../services/wsService'

export function useCamera() {
  const videoRef = ref(null)
  const canvasRef = ref(null)
  const isStreaming = ref(false)
  const error = ref(null)

  let stream = null
  let captureInterval = null

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
      startCapture()

    } catch (e) {
      console.error('Camera error:', e)
      error.value = getCameraErrorMessage(e)
    }
  }

  /**
   * 关闭摄像头
   */
  function stopCamera() {
    if (captureInterval) {
      clearInterval(captureInterval)
      captureInterval = null
    }

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
   * 开始定时截帧
   */
  function startCapture() {
    // 每 2 秒截取一帧
    captureInterval = setInterval(() => {
      captureFrame()
    }, 2000)
  }

  /**
   * 截取当前帧
   */
  function captureFrame() {
    if (!videoRef.value || !isStreaming.value) return

    const canvas = document.createElement('canvas')
    const video = videoRef.value

    // 设置 canvas 尺寸（限制最大宽度为 640）
    const maxWidth = 640
    const scale = Math.min(1, maxWidth / video.videoWidth)
    canvas.width = video.videoWidth * scale
    canvas.height = video.videoHeight * scale

    // 绘制视频帧到 canvas
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    // 转换为 base64 JPEG（质量 0.6）
    const imageBase64 = canvas.toDataURL('image/jpeg', 0.6)
      .replace('data:image/jpeg;base64,', '')

    // 发送到服务器
    wsService.sendVideoFrame(imageBase64)
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
