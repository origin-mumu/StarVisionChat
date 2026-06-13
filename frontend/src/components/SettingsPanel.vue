<template>
  <div class="settings-container">
    <button class="btn-icon" @click="showSettings = !showSettings" data-tooltip="设置">
      <el-icon><Setting /></el-icon>
    </button>

    <!-- 设置面板 -->
    <Transition name="ui-fade">
      <div v-if="showSettings" class="settings-panel glass-mid">
        <div class="panel-header">
          <span class="text-h3">MiMo 配置</span>
          <button class="btn-icon" @click="showSettings = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <div class="settings-form">
          <!-- ── API 连接 ── -->
          <div class="section-label">
            <span class="section-line"></span>
            <span class="section-text">API 连接</span>
            <span class="section-line"></span>
          </div>

          <!-- API Key -->
          <div class="form-group">
            <label class="form-label text-caption">API Key <span class="required">*</span></label>
            <div class="input-with-toggle">
              <input
                v-model="apiKey"
                :type="showApiKey ? 'text' : 'password'"
                class="input-field"
                placeholder="输入你的 MiMo API Key"
              />
              <button class="btn-icon toggle-btn" @click="showApiKey = !showApiKey">
                <el-icon v-if="showApiKey"><Hide /></el-icon>
                <el-icon v-else><View /></el-icon>
              </button>
            </div>
          </div>

          <!-- API Base URL -->
          <div class="form-group">
            <label class="form-label text-caption">Base URL</label>
            <input
              v-model="baseUrl"
              class="input-field"
              placeholder="https://token-plan-cn.xiaomimimo.com/v1"
            />
            <span class="form-hint">TokenPlan 会员专属地址</span>
          </div>

          <!-- ── 模型配置 ── -->
          <div class="section-label">
            <span class="section-line"></span>
            <span class="section-text">模型配置</span>
            <span class="section-line"></span>
          </div>

          <!-- 对话模型 -->
          <div class="form-group">
            <label class="form-label text-caption">对话模型（多模态）</label>
            <input
              v-model="chatModel"
              class="input-field input-readonly"
              readonly
            />
            <span class="form-hint">支持文本、图像、音频、视频输入</span>
          </div>

          <!-- 语音识别 -->
          <div class="form-group">
            <label class="form-label text-caption">语音识别 (ASR)</label>
            <input
              v-model="asrModel"
              class="input-field input-readonly"
              readonly
            />
          </div>

          <!-- 语音合成 -->
          <div class="form-group">
            <label class="form-label text-caption">语音合成 (TTS)</label>
            <input
              v-model="ttsModel"
              class="input-field input-readonly"
              readonly
            />
          </div>

          <!-- TTS 音色 -->
          <div class="form-group">
            <label class="form-label text-caption">TTS 音色</label>
            <div class="select-wrapper">
              <select v-model="ttsVoice" class="input-field select-field">
                <option
                  v-for="option in ttsVoiceOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
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
const baseUrl = ref('https://token-plan-cn.xiaomimimo.com/v1')
const chatModel = ref('mimo-v2.5')
const asrModel = ref('mimo-v2.5-asr')
const ttsModel = ref('mimo-v2.5-tts')
const ttsVoice = ref('mimo_default')

const ttsVoiceOptions = [
  { value: 'mimo_default', label: 'MiMo 默认' },
  { value: 'Chloe', label: 'Chloe' },
]

// 从 localStorage 加载配置
onMounted(() => {
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      apiKey.value = config.apiKey || ''
      baseUrl.value = config.baseUrl || 'https://token-plan-cn.xiaomimimo.com/v1'
      chatModel.value = config.chatModel || 'mimo-v2.5'
      asrModel.value = config.asrModel || 'mimo-v2.5-asr'
      ttsModel.value = config.ttsModel || 'mimo-v2.5-tts'
      ttsVoice.value = config.ttsVoice || 'mimo_default'

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
    alert('请输入 MiMo API Key')
    return
  }

  // 保存到 localStorage
  const config = {
    apiKey: apiKey.value,
    baseUrl: baseUrl.value,
    chatModel: chatModel.value,
    asrModel: asrModel.value,
    ttsModel: ttsModel.value,
    ttsVoice: ttsVoice.value,
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
    chat_model: chatModel.value,
    asr_model: asrModel.value,
    tts_model: ttsModel.value,
    tts_voice: ttsVoice.value,
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
  width: 340px;
  max-height: 80vh;
  overflow-y: auto;
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

/* Section divider */
.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
}

.section-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}

.section-text {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

/* 表单 */
.settings-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-label {
  color: var(--ink-soft);
  font-weight: 500;
}

.required {
  color: var(--accent);
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

.input-readonly {
  background: var(--surface-hover);
  color: var(--ink-soft);
  cursor: default;
  opacity: 0.85;
}

.form-hint {
  font-size: 11px;
  color: var(--ink-muted);
  opacity: 0.7;
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
