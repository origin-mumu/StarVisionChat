<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { wsService } from '../services/wsService'
import {
  View,
  Hide,
  Check,
} from '@element-plus/icons-vue'

const emit = defineEmits(['done'])

const isVisible = ref(false)
const showApiKey = ref(false)

/* ─── Form fields ─── */
const apiKey = ref('')
const baseUrl = ref('https://token-plan-cn.xiaomimimo.com/v1')
const chatModel = ref('mimo-v2.5')
const asrModel = ref('mimo-v2.5-asr')
const ttsModel = ref('mimo-v2.5-tts')
const ttsVoice = ref('mimo_default')

const saving = ref(false)
const errorMsg = ref('')

/* ─── TTS 音色选项 ─── */
const ttsVoiceOptions = [
  { value: 'mimo_default', label: 'MiMo 默认' },
  { value: 'Chloe', label: 'Chloe' },
]

/* ─── Load saved config ─── */
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
    } catch { /* ignore */ }
  }
  requestAnimationFrame(() => { isVisible.value = true })
})

function saveAndEnter() {
  errorMsg.value = ''

  if (!apiKey.value.trim()) {
    errorMsg.value = '请输入 MiMo API Key'
    return
  }

  saving.value = true

  // Save to localStorage
  const config = {
    apiKey: apiKey.value.trim(),
    baseUrl: baseUrl.value.trim(),
    chatModel: chatModel.value,
    asrModel: asrModel.value,
    ttsModel: ttsModel.value,
    ttsVoice: ttsVoice.value,
    configured: true,
  }
  localStorage.setItem('starvisionchat_config', JSON.stringify(config))

  // Send to backend
  const wsConfig = {
    api_key: config.apiKey,
    base_url: config.baseUrl,
    chat_model: config.chatModel,
    asr_model: config.asrModel,
    tts_model: config.ttsModel,
    tts_voice: config.ttsVoice,
  }

  if (wsService.ws && wsService.ws.readyState === WebSocket.OPEN) {
    wsService.send('config_update', wsConfig)
  } else {
    // Wait for connection
    const onConnected = () => {
      wsService.send('config_update', wsConfig)
      wsService.off('connected', onConnected)
    }
    wsService.on('connected', onConnected)
    if (!wsService.ws) {
      wsService.connect()
    }
  }

  // Transition out
  setTimeout(() => {
    isVisible.value = false
    setTimeout(() => emit('done'), 400)
  }, 300)
}

function skipConfig() {
  isVisible.value = false
  setTimeout(() => emit('done'), 400)
}
</script>

<template>
  <div class="config-page" :class="{ visible: isVisible }">
    <div class="config-card">
      <div class="config-header">
        <h2>系统配置</h2>
        <p>配置 MiMo API 参数以开始使用</p>
      </div>

      <div class="config-form">
        <!-- ── API 连接 ── -->
        <div class="section-label">
          <span class="section-line"></span>
          <span class="section-text">API 连接</span>
          <span class="section-line"></span>
        </div>

        <!-- API Key -->
        <div class="form-group">
          <label class="form-label">API Key <span class="required">*</span></label>
          <div class="input-with-toggle">
            <input
              v-model="apiKey"
              :type="showApiKey ? 'text' : 'password'"
              class="form-input"
              placeholder="输入你的 MiMo API Key"
              @keyup.enter="saveAndEnter"
            />
            <button class="toggle-vis" @click="showApiKey = !showApiKey">
              <el-icon v-if="showApiKey"><Hide /></el-icon>
              <el-icon v-else><View /></el-icon>
            </button>
          </div>
        </div>

        <!-- API Base URL -->
        <div class="form-group">
          <label class="form-label">Base URL</label>
          <input
            v-model="baseUrl"
            class="form-input"
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
          <label class="form-label">对话模型（多模态）</label>
          <input
            v-model="chatModel"
            class="form-input form-input-readonly"
            readonly
          />
          <span class="form-hint">支持文本、图像、音频、视频输入</span>
        </div>

        <!-- 语音识别 & 语音合成 并排 -->
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">语音识别 (ASR)</label>
            <input
              v-model="asrModel"
              class="form-input form-input-readonly"
              readonly
            />
          </div>
          <div class="form-group">
            <label class="form-label">语音合成 (TTS)</label>
            <input
              v-model="ttsModel"
              class="form-input form-input-readonly"
              readonly
            />
          </div>
        </div>

        <!-- TTS 音色 -->
        <div class="form-group">
          <label class="form-label">TTS 音色</label>
          <select v-model="ttsVoice" class="form-input form-select">
            <option
              v-for="option in ttsVoiceOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>

        <!-- Error -->
        <p v-if="errorMsg" class="form-error">{{ errorMsg }}</p>

        <!-- Actions -->
        <div class="form-actions">
          <button class="btn-skip" @click="skipConfig">稍后配置</button>
          <button class="btn-primary" @click="saveAndEnter" :disabled="saving">
            <el-icon v-if="!saving"><Check /></el-icon>
            <span>{{ saving ? '保存中...' : '保存并进入' }}</span>
          </button>
        </div>

        <p class="form-tip">配置保存在浏览器本地，下次打开自动加载</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-page {
  position: fixed;
  inset: 0;
  z-index: 99998;
  background-color: var(--canvas);
  background-image:
    radial-gradient(circle at 25% 35%, var(--orb-1) 0%, transparent 45%),
    radial-gradient(circle at 75% 65%, var(--orb-2) 0%, transparent 45%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  opacity: 0;
  transition: opacity 0.4s ease;
}
.config-page.visible {
  opacity: 1;
}

.config-card {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: var(--shadow-card-hover);
  animation: card-rise 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: 0.15s;
}

@keyframes card-rise {
  from { opacity: 0; transform: translateY(24px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.config-header {
  text-align: center;
  margin-bottom: 32px;
}

.config-header h2 {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
  margin: 0 0 8px;
  letter-spacing: 0.02em;
}

.config-header p {
  font-size: 14px;
  color: var(--ink-muted);
  margin: 0;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* Section divider */
.section-label {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0;
}

.section-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}

.section-text {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
}

.required {
  color: var(--accent);
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--canvas);
  color: var(--ink);
  font-size: 14px;
  font-family: inherit;
  transition: all 0.2s;
  outline: none;
}
.form-input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-soft);
  background: var(--surface-hover);
}
.form-input::placeholder {
  color: var(--ink-muted);
  opacity: 0.6;
}

.form-input-readonly {
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

.form-select {
  appearance: none;
  cursor: pointer;
  padding-right: 32px;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%238A7E74' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.input-with-toggle {
  position: relative;
}
.input-with-toggle .form-input {
  padding-right: 44px;
}

.toggle-vis {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.toggle-vis:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.form-error {
  font-size: 13px;
  color: #e74c3c;
  margin: 0;
  text-align: center;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.btn-skip {
  flex: 1;
  padding: 12px 20px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-skip:hover {
  background: var(--surface-hover);
  border-color: var(--border-interactive);
  color: var(--ink);
}

.btn-primary {
  flex: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 999px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--shadow-button);
  transition: all 0.25s;
}
.btn-primary:hover:not(:disabled) {
  box-shadow: var(--shadow-button-hover);
  transform: translateY(-1px);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-tip {
  font-size: 12px;
  color: var(--ink-muted);
  text-align: center;
  margin: 0;
  opacity: 0.7;
}

/* Responsive */
@media (max-width: 480px) {
  .config-card {
    padding: 28px 20px;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
