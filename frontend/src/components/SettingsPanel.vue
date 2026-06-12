<template>
  <div class="settings-container">
    <button class="btn-icon" @click="showSettings = !showSettings" data-tooltip="设置">
      <el-icon><Setting /></el-icon>
    </button>

    <!-- 设置面板 -->
    <Transition name="ui-fade">
      <div v-if="showSettings" class="settings-panel glass-mid">
        <div class="panel-header">
          <span class="text-h3">API 配置</span>
          <button class="btn-icon" @click="showSettings = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <div class="settings-form">
          <!-- API Key -->
          <div class="form-group">
            <label class="form-label text-caption">API Key</label>
            <div class="input-with-toggle">
              <input
                v-model="apiKey"
                :type="showApiKey ? 'text' : 'password'"
                class="input-field"
                placeholder="输入你的 API Key"
              />
              <button class="btn-icon toggle-btn" @click="showApiKey = !showApiKey">
                <el-icon v-if="showApiKey"><Hide /></el-icon>
                <el-icon v-else><View /></el-icon>
              </button>
            </div>
          </div>

          <!-- API Base URL -->
          <div class="form-group">
            <label class="form-label text-caption">API Base URL</label>
            <input
              v-model="baseUrl"
              class="input-field"
              placeholder="https://api.openai.com/v1"
            />
          </div>

          <!-- 视觉模型 -->
          <div class="form-group">
            <label class="form-label text-caption">视觉模型</label>
            <div class="select-wrapper">
              <select v-model="visionModel" class="input-field select-field">
                <option value="gpt-4o-mini">GPT-4o Mini (经济)</option>
                <option value="gpt-4o">GPT-4o (高质量)</option>
              </select>
            </div>
          </div>

          <!-- 对话模型 -->
          <div class="form-group">
            <label class="form-label text-caption">对话模型</label>
            <div class="select-wrapper">
              <select v-model="chatModel" class="input-field select-field">
                <option value="gpt-4o-mini">GPT-4o Mini (经济)</option>
                <option value="gpt-4o">GPT-4o (高质量)</option>
              </select>
            </div>
          </div>

          <!-- TTS 语音 -->
          <div class="form-group">
            <label class="form-label text-caption">TTS 语音</label>
            <div class="select-wrapper">
              <select v-model="ttsVoice" class="input-field select-field">
                <option value="zh-CN-XiaoxiaoNeural">晓晓 (女声)</option>
                <option value="zh-CN-YunxiNeural">云希 (男声)</option>
                <option value="zh-CN-YunyangNeural">云扬 (男声)</option>
                <option value="zh-CN-XiaohanNeural">晓涵 (女声)</option>
              </select>
            </div>
          </div>

          <!-- 保存按钮 -->
          <button class="btn-primary" style="width: 100%" @click="saveSettings">
            <el-icon><Check /></el-icon>
            保存配置
          </button>

          <p class="form-tip text-caption">
            <el-icon><InfoFilled /></el-icon>
            配置会保存在浏览器本地，下次打开自动加载
          </p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Setting, Close, Hide, View, Check, InfoFilled } from '@element-plus/icons-vue'
import { wsService } from '../services/wsService'

const showSettings = ref(false)
const showApiKey = ref(false)

const apiKey = ref('')
const baseUrl = ref('https://api.openai.com/v1')
const visionModel = ref('gpt-4o-mini')
const chatModel = ref('gpt-4o-mini')
const ttsVoice = ref('zh-CN-XiaoxiaoNeural')

// 从 localStorage 加载配置
onMounted(() => {
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      apiKey.value = config.apiKey || ''
      baseUrl.value = config.baseUrl || 'https://api.openai.com/v1'
      visionModel.value = config.visionModel || 'gpt-4o-mini'
      chatModel.value = config.chatModel || 'gpt-4o-mini'
      ttsVoice.value = config.ttsVoice || 'zh-CN-XiaoxiaoNeural'

      // 如果有保存的配置，自动发送到后端
      if (apiKey.value) {
        sendConfigToBackend()
      }
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }
})

// 保存配置
function saveSettings() {
  if (!apiKey.value.trim()) {
    alert('请输入 API Key')
    return
  }

  // 保存到 localStorage
  const config = {
    apiKey: apiKey.value,
    baseUrl: baseUrl.value,
    visionModel: visionModel.value,
    chatModel: chatModel.value,
    ttsVoice: ttsVoice.value
  }
  localStorage.setItem('starvisionchat_config', JSON.stringify(config))

  // 发送到后端
  sendConfigToBackend()

  showSettings.value = false
}

// 发送配置到后端
function sendConfigToBackend() {
  const config = {
    api_key: apiKey.value,
    base_url: baseUrl.value,
    vision_model: visionModel.value,
    chat_model: chatModel.value,
    tts_voice: ttsVoice.value
  }

  // 如果 WebSocket 未连接，等待连接后再发送
  if (!wsService.ws || wsService.ws.readyState !== WebSocket.OPEN) {
    console.log('WebSocket not connected, will send config when connected')
    const onConnected = () => {
      wsService.send('config_update', config)
      wsService.off('connected', onConnected)
    }
    wsService.on('connected', onConnected)

    // 确保 WebSocket 已连接
    if (!wsService.ws) {
      wsService.connect()
    }
  } else {
    wsService.send('config_update', config)
  }
}
</script>

<style scoped>
.settings-container {
  position: relative;
}

/* 设置面板 */
.settings-panel {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 320px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--glass-mid);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--shadow-card);
  z-index: 100;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 0.5px solid var(--border);
}

/* 表单 */
.settings-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  color: var(--ink-soft);
  font-weight: 500;
}

.input-with-toggle {
  position: relative;
}

.input-with-toggle .input-field {
  padding-right: 48px;
}

.toggle-btn {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
}

.select-wrapper {
  position: relative;
}

.select-field {
  appearance: none;
  padding-right: 36px;
  cursor: pointer;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid var(--ink-muted);
  pointer-events: none;
}

.form-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  text-align: center;
  color: var(--ink-muted);
}
</style>
