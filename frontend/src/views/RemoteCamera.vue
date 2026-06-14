<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const sessionId = route.query.session || ''
const statusText = ref('正在连接...')
const connected = ref(false)
const errorText = ref('')

let pc = null
let ws = null
let localStream = null

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws/camera`

async function start() {
  if (!sessionId) {
    errorText.value = '缺少会话 ID，请重新扫码'
    statusText.value = '错误'
    return
  }

  // 检查安全上下文
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    errorText.value = '需要 HTTPS 安全连接才能使用摄像头。\n请在手机 Chrome 地址栏输入 chrome://flags 搜索 insecure origin 并添加此地址。'
    statusText.value = '需要 HTTPS'
    return
  }

  try {
    // 1. 获取摄像头
    localStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'environment' },
      audio: false,
    })
    // 显示本地画面
    const video = document.getElementById('local-video')
    if (video) {
      video.srcObject = localStream
      await video.play()
    }

    // 2. 连接 WebSocket 用于信令
    statusText.value = '正在建立信令通道...'
    ws = new WebSocket(WS_URL)

    ws.onopen = async () => {
      // 3. 注册为 camera 端
      ws.send(JSON.stringify({ type: 'camera_register', data: { session: sessionId } }))
    }

    ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'camera_registered') {
        statusText.value = '正在建立 P2P 连接...'
        await createOffer()
      } else if (msg.type === 'webrtc_answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(msg.data))
        statusText.value = '连接成功'
        connected.value = true
      } else if (msg.type === 'webrtc_ice') {
        try {
          await pc.addIceCandidate(new RTCIceCandidate(msg.data))
        } catch { /* ignore */ }
      } else if (msg.type === 'camera_disconnect') {
        statusText.value = '电脑端已断开'
      }
    }

    ws.onerror = () => {
      errorText.value = '信令连接失败'
      statusText.value = '错误'
    }

    ws.onclose = () => {
      if (!connected.value) {
        errorText.value = '信令连接断开'
      }
    }
  } catch (err) {
    if (err.name === 'NotAllowedError') {
      errorText.value = '请允许摄像头权限'
    } else if (err.name === 'NotFoundError') {
      errorText.value = '未检测到摄像头'
    } else if (err.message?.includes('getUserMedia') || !navigator.mediaDevices) {
      errorText.value = '需要 HTTPS 或 localhost 才能使用摄像头。请在手机 Chrome 打开 chrome://flags/#unsafely-treat-insecure-origin-as-secure 并将此地址加入白名单。'
    } else {
      errorText.value = `启动失败: ${err.message}`
    }
    statusText.value = '错误'
  }
}

async function createOffer() {
  const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] }
  pc = new RTCPeerConnection(config)

  // 添加本地视频流
  localStream.getTracks().forEach(track => pc.addTrack(track, localStream))

  // ICE candidate 发送给后端
  pc.onicecandidate = (event) => {
    if (event.candidate && ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'webrtc_ice', data: { session: sessionId, candidate: event.candidate.toJSON() } }))
    }
  }

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'connected') {
      statusText.value = '连接成功'
      connected.value = true
    } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
      statusText.value = '连接断开'
      errorText.value = 'P2P 连接失败，请重试'
    }
  }

  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)
  ws.send(JSON.stringify({ type: 'webrtc_offer', data: { session: sessionId, sdp: offer } }))
}

onMounted(() => { start() })

onBeforeUnmount(() => {
  if (pc) pc.close()
  if (ws) ws.close()
  if (localStream) localStream.getTracks().forEach(t => t.stop())
})
</script>

<template>
  <div class="remote-camera">
    <div v-if="errorText" class="rc-error">
      <h2>{{ errorText }}</h2>
      <p>{{ sessionId ? `会话: ${sessionId}` : '' }}</p>
    </div>
    <div v-else class="rc-connected">
      <video id="local-video" autoplay playsinline muted class="rc-video"></video>
      <div class="rc-status" :class="{ done: connected }">{{ statusText }}</div>
    </div>
  </div>
</template>

<style scoped>
.remote-camera {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.rc-error {
  text-align: center;
  color: #f56c6c;
  padding: 20px;
}
.rc-error h2 { margin-bottom: 8px; font-size: 16px; }
.rc-error p { font-size: 12px; opacity: 0.6; }

.rc-connected {
  position: relative;
  width: 100%;
  height: 100%;
}

.rc-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.rc-status {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  border-radius: 20px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 14px;
  backdrop-filter: blur(8px);
}
.rc-status.done {
  background: rgba(76,175,80,0.6);
  animation: fadeOut 2s forwards 1s;
}

@keyframes fadeOut {
  to { opacity: 0; }
}
</style>
