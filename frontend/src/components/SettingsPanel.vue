<template>
  <div class="settings-container">
    <button class="btn-icon" @click="showSettings = !showSettings" data-tooltip="设置">
      <el-icon><Setting /></el-icon>
    </button>

    <!-- 设置面板 -->
    <Transition name="ui-fade">
      <div v-if="showSettings" class="settings-panel glass-mid">
        <div class="panel-header">
          <span class="text-h3">模型配置</span>
          <button class="btn-icon" @click="showSettings = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <div class="settings-form">
          <!-- Model Provider Selection -->
          <div class="form-group">
            <label class="form-label text-caption">模型选择</label>
            <div class="provider-tabs">
              <button
                class="provider-tab"
                :class="{ active: modelProvider === 'mimo' }"
                @click="modelProvider = 'mimo'"
              >
                MiMo
              </button>
              <button
                class="provider-tab"
                :class="{ active: modelProvider === 'qwen' }"
                @click="modelProvider = 'qwen'"
              >
                Qwen
              </button>
            </div>
          </div>

          <!-- MiMo Config -->
          <template v-if="modelProvider === 'mimo'">
            <div class="section-label">
              <span class="section-line"></span>
              <span class="section-text">MiMo 配置</span>
              <span class="section-line"></span>
            </div>

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

            <div class="form-group">
              <label class="form-label text-caption">Base URL</label>
              <input v-model="baseUrl" class="input-field" placeholder="https://token-plan-cn.xiaomimimo.com/v1" />
              <span class="form-hint">TokenPlan 会员专属地址</span>
            </div>

            <div class="form-group">
              <label class="form-label text-caption">对话模型</label>
              <input v-model="chatModel" class="input-field input-readonly" readonly />
            </div>

            <div class="form-group">
              <label class="form-label text-caption">语音识别</label>
              <input v-model="asrModel" class="input-field input-readonly" readonly />
            </div>

            <div class="form-group">
              <label class="form-label text-caption">语音合成</label>
              <input v-model="ttsModel" class="input-field input-readonly" readonly />
            </div>

            <div class="form-group">
              <label class="form-label text-caption">TTS 音色</label>
              <div class="select-wrapper">
                <select v-model="ttsVoice" class="input-field select-field">
                  <option v-for="opt in ttsVoiceOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>
          </template>

          <!-- Qwen Config -->
          <template v-if="modelProvider === 'qwen'">
            <div class="section-label">
              <span class="section-line"></span>
              <span class="section-text">Qwen 配置</span>
              <span class="section-line"></span>
            </div>

            <div class="form-group">
              <label class="form-label text-caption">API Key <span class="required">*</span></label>
              <div class="input-with-toggle">
                <input
                  v-model="qwenApiKey"
                  :type="showQwenApiKey ? 'text' : 'password'"
                  class="input-field"
                  placeholder="输入你的 Qwen API Key"
                />
                <button class="btn-icon toggle-btn" @click="showQwenApiKey = !showQwenApiKey">
                  <el-icon v-if="showQwenApiKey"><Hide /></el-icon>
                  <el-icon v-else><View /></el-icon>
                </button>
              </div>
              <span class="form-hint">在阿里云百炼平台获取</span>
            </div>

            <div class="form-group">
              <label class="form-label text-caption">模型</label>
              <div class="select-wrapper">
                <select v-model="qwenModel" class="input-field select-field">
                  <option v-for="opt in qwenModelOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label text-caption">音色</label>
              <div class="select-wrapper">
                <select v-model="qwenVoice" class="input-field select-field">
                  <option v-for="opt in qwenVoiceOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label text-caption">地域</label>
              <div class="select-wrapper">
                <select v-model="qwenRegion" class="input-field select-field">
                  <option value="cn">华北2（北京）</option>
                  <option value="intl">新加坡</option>
                </select>
              </div>
            </div>
          </template>

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
const showQwenApiKey = ref(false)

/* ─── Model provider ─── */
const modelProvider = ref('mimo')

/* ─── MiMo fields ─── */
const apiKey = ref('')
const baseUrl = ref('https://token-plan-cn.xiaomimimo.com/v1')
const chatModel = ref('mimo-v2.5')
const asrModel = ref('mimo-v2.5-asr')
const ttsModel = ref('mimo-v2.5-tts')
const ttsVoice = ref('mimo_default')

/* ─── Qwen fields ─── */
const qwenApiKey = ref('')
const qwenModel = ref('qwen3.5-omni-plus-realtime')
const qwenVoice = ref('Ethan')
const qwenRegion = ref('cn')

/* ─── Options ─── */
const ttsVoiceOptions = [
  { value: 'mimo_default', label: 'MiMo 默认' },
  { value: 'Chloe', label: 'Chloe' },
]

const qwenVoiceOptions = [
  { value: 'Ethan', label: 'Ethan (男声)' },
  { value: 'Chloe', label: 'Chloe (女声)' },
]

const qwenModelOptions = [
  { value: 'qwen3.5-omni-plus-realtime', label: 'Qwen3.5 Omni Plus (高质量)' },
  { value: 'qwen3.5-omni-flash-realtime', label: 'Qwen3.5 Omni Flash (快速)' },
]

// 从 localStorage 加载配置
onMounted(() => {
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      modelProvider.value = config.modelProvider || 'mimo'

      // MiMo config
      apiKey.value = config.apiKey || ''
      baseUrl.value = config.baseUrl || 'https://token-plan-cn.xiaomimimo.com/v1'
      chatModel.value = config.chatModel || 'mimo-v2.5'
      asrModel.value = config.asrModel || 'mimo-v2.5-asr'
      ttsModel.value = config.ttsModel || 'mimo-v2.5-tts'
      ttsVoice.value = config.ttsVoice || 'mimo_default'

      // Qwen config
      qwenApiKey.value = config.qwenApiKey || ''
      qwenModel.value = config.qwenModel || 'qwen3.5-omni-plus-realtime'
      qwenVoice.value = config.qwenVoice || 'Ethan'
      qwenRegion.value = config.qwenRegion || 'cn'

      // 如果有保存的配置，自动发送到后端
      if (apiKey.value || qwenApiKey.value) {
        sendConfigToBackend()
      }
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }
})

// 保存配置
function saveSettings() {
  // Validate based on selected provider
  if (modelProvider.value === 'mimo' && !apiKey.value.trim()) {
    alert('请输入 MiMo API Key')
    return
  }
  if (modelProvider.value === 'qwen' && !qwenApiKey.value.trim()) {
    alert('请输入 Qwen API Key')
    return
  }

  // 保存到 localStorage
  const config = {
    modelProvider: modelProvider.value,
    // MiMo
    apiKey: apiKey.value,
    baseUrl: baseUrl.value,
    chatModel: chatModel.value,
    asrModel: asrModel.value,
    ttsModel: ttsModel.value,
    ttsVoice: ttsVoice.value,
    // Qwen
    qwenApiKey: qwenApiKey.value,
    qwenModel: qwenModel.value,
    qwenVoice: qwenVoice.value,
    qwenRegion: qwenRegion.value,
  }
  localStorage.setItem('starvisionchat_config', JSON.stringify(config))

  // 发送到后端
  sendConfigToBackend()

  // 触发配置更新事件，通知其他组件
  window.dispatchEvent(new Event('config-updated'))

  showSettings.value = false
}

// 发送配置到后端
function sendConfigToBackend() {
  const config = {
    model_provider: modelProvider.value,
    // MiMo
    api_key: apiKey.value,
    base_url: baseUrl.value,
    chat_model: chatModel.value,
    asr_model: asrModel.value,
    tts_model: ttsModel.value,
    tts_voice: ttsVoice.value,
    // Qwen
    qwen_api_key: qwenApiKey.value,
    qwen_model: qwenModel.value,
    qwen_voice: qwenVoice.value,
    qwen_region: qwenRegion.value,
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
  width: 360px;
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

/* Provider tabs */
.provider-tabs {
  display: flex;
  gap: 6px;
  background: var(--canvas);
  border-radius: 10px;
  padding: 3px;
}

.provider-tab {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-tab.active {
  background: var(--accent);
  color: #fff;
}

.provider-tab:hover:not(.active) {
  background: var(--surface-hover);
  color: var(--ink);
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
