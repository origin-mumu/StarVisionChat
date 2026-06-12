<template>
  <div class="video-container glass-card">
    <!-- 视频头部 -->
    <div class="video-header">
      <div class="header-left">
        <span class="status-dot" :class="{ active: isStreaming }"></span>
        <span class="text-body-small">{{ isStreaming ? '摄像头已开启' : '摄像头未开启' }}</span>
      </div>
      <div class="header-right">
        <button
          class="btn-icon"
          @click="captureFrame"
          :disabled="!isStreaming"
          data-tooltip="手动截帧"
        >
          <el-icon><Camera /></el-icon>
        </button>
      </div>
    </div>

    <!-- 视频画面 -->
    <div class="video-wrapper">
      <video
        ref="videoRef"
        autoplay
        muted
        playsinline
        class="video-element"
      />

      <!-- 占位符 -->
      <div v-if="!isStreaming" class="video-placeholder">
        <div class="placeholder-icon">
          <el-icon :size="48"><VideoCamera /></el-icon>
        </div>
        <p class="text-h3">开启摄像头</p>
        <p class="text-caption">让 AI 看到你的世界</p>
      </div>

      <!-- 语音指示器 -->
      <Transition name="ui-fade">
        <div v-if="isSpeaking" class="speaking-indicator">
          <div class="pulse-ring"></div>
          <span>正在聆听...</span>
        </div>
      </Transition>
    </div>

    <!-- 控制按钮 -->
    <div class="video-controls">
      <button
        v-if="!isStreaming"
        class="btn-primary btn-large"
        @click="startCamera"
        :disabled="loading"
      >
        <el-icon v-if="loading" class="loading-spinner"><Loading /></el-icon>
        <el-icon v-else><VideoCamera /></el-icon>
        {{ loading ? '启动中...' : '开启摄像头' }}
      </button>
      <button
        v-else
        class="btn-secondary btn-large"
        @click="stopCamera"
      >
        <el-icon><VideoPause /></el-icon>
        关闭摄像头
      </button>

      <button
        v-if="!isRecording"
        class="btn-primary btn-large"
        @click="startMicrophone"
        :disabled="!isStreaming"
      >
        <el-icon><Microphone /></el-icon>
        开启麦克风
      </button>
      <button
        v-else
        class="btn-secondary btn-large"
        @click="stopMicrophone"
      >
        <el-icon><Mute /></el-icon>
        关闭麦克风
      </button>
    </div>

    <!-- 错误提示 -->
    <Transition name="ui-fade">
      <div v-if="cameraError || micError" class="error-message">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ cameraError || micError }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { VideoCamera, Camera, VideoPause, Microphone, Mute, Loading, WarningFilled } from '@element-plus/icons-vue'
import { useCamera } from '../composables/useCamera'
import { useMicrophone } from '../composables/useMicrophone'

const loading = ref(false)

const {
  videoRef,
  isStreaming,
  error: cameraError,
  startCamera: initCamera,
  stopCamera,
  captureFrame
} = useCamera()

const {
  isRecording,
  isSpeaking,
  error: micError,
  startMicrophone: initMic,
  stopMicrophone
} = useMicrophone()

async function startCamera() {
  loading.value = true
  await initCamera()
  loading.value = false
}

async function startMicrophone() {
  await initMic()
}
</script>

<style scoped>
.video-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  gap: var(--space-4);
}

/* 头部 */
.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-right {
  display: flex;
  gap: var(--space-2);
}

/* 视频区域 */
.video-wrapper {
  flex: 1;
  position: relative;
  background: var(--canvas-deep);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 300px;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 占位符 */
.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}

.placeholder-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-mid);
  border-radius: var(--radius-xl);
  color: var(--ink-muted);
}

.video-placeholder p {
  color: var(--ink-muted);
  text-align: center;
}

/* 语音指示器 */
.speaking-indicator {
  position: absolute;
  bottom: var(--space-4);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 20px;
  background: var(--glass-top);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-full);
  border: 0.5px solid var(--glass-border);
  color: #4CAF50;
  font-size: var(--text-body-small);
  font-weight: 500;
}

.pulse-ring {
  width: 10px;
  height: 10px;
  background: #4CAF50;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.6; }
}

/* 控制按钮 */
.video-controls {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  flex-wrap: wrap;
}

/* 错误提示 */
.error-message {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.2);
  border-radius: var(--radius-md);
  color: #F44336;
  font-size: var(--text-body-small);
}

/* 响应式 */
@media (max-width: 768px) {
  .video-controls {
    flex-direction: column;
  }

  .video-controls .btn-primary,
  .video-controls .btn-secondary {
    width: 100%;
  }
}
</style>
