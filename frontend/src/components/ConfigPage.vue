<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { wsService } from '../services/wsService'
import {
  View,
  Hide,
  Check,
  ArrowLeft,
} from '@element-plus/icons-vue'

const router = useRouter()

const isVisible = ref(false)
const showApiKey = ref(false)
const showQwenApiKey = ref(false)

/* ─── Model provider ─── */
const modelProvider = ref('qwen')  // qwen / mimo

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

const saving = ref(false)
const errorMsg = ref('')

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

/* ─── Computed ─── */
const currentApiKey = computed(() => {
  return modelProvider.value === 'mimo' ? apiKey.value : qwenApiKey.value
})

/* ─── Load saved config ─── */
onMounted(() => {
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      modelProvider.value = config.modelProvider || 'qwen'

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
    } catch { /* ignore */ }
  }
  requestAnimationFrame(() => { isVisible.value = true })
})

function saveAndEnter() {
  errorMsg.value = ''

  // Validate based on selected provider
  if (modelProvider.value === 'mimo' && !apiKey.value.trim()) {
    errorMsg.value = '请输入 MiMo API Key'
    return
  }
  if (modelProvider.value === 'qwen' && !qwenApiKey.value.trim()) {
    errorMsg.value = '请输入 Qwen API Key'
    return
  }

  saving.value = true

  // Save to localStorage
  const config = {
    modelProvider: modelProvider.value,
    // MiMo
    apiKey: apiKey.value.trim(),
    baseUrl: baseUrl.value.trim(),
    chatModel: chatModel.value,
    asrModel: asrModel.value,
    ttsModel: ttsModel.value,
    ttsVoice: ttsVoice.value,
    // Qwen
    qwenApiKey: qwenApiKey.value.trim(),
    qwenModel: qwenModel.value,
    qwenVoice: qwenVoice.value,
    qwenRegion: qwenRegion.value,
    configured: true,
  }
  localStorage.setItem('starvisionchat_config', JSON.stringify(config))

  // Send to backend
  const wsConfig = {
    model_provider: config.modelProvider,
    // MiMo
    api_key: config.apiKey,
    base_url: config.baseUrl,
    chat_model: config.chatModel,
    asr_model: config.asrModel,
    tts_model: config.ttsModel,
    tts_voice: config.ttsVoice,
    // Qwen
    qwen_api_key: config.qwenApiKey,
    qwen_model: config.qwenModel,
    qwen_voice: config.qwenVoice,
    qwen_region: config.qwenRegion,
  }

  if (wsService.ws && wsService.ws.readyState === WebSocket.OPEN) {
    wsService.send('config_update', wsConfig)
  } else {
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
    setTimeout(() => router.push('/chat'), 400)
  }, 300)
}

function skipConfig() {
  isVisible.value = false
  setTimeout(() => router.push('/chat'), 400)
}

function goBack() {
  isVisible.value = false
  setTimeout(() => {
    router.replace('/')
  }, 400)
}
</script>

<template>
  <div class="config-page" :class="{ visible: isVisible }">
    <div class="config-card">
      <div class="config-header">
        <button class="back-btn" @click="goBack" title="返回封面">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <h2>系统配置</h2>
        <p>选择模型并配置 API 参数</p>
      </div>

      <div class="config-form">
        <!-- Model Provider Selection -->
        <div class="form-group">
          <label class="form-label">模型选择</label>
          <div class="provider-tabs">
            <button
              class="provider-tab"
              :class="{ active: modelProvider === 'qwen' }"
              @click="modelProvider = 'qwen'"
            >
              Qwen
            </button>
            <button
              class="provider-tab"
              :class="{ active: modelProvider === 'mimo' }"
              @click="modelProvider = 'mimo'"
            >
              MiMo
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
            <label class="form-label">API Key <span class="required">*</span></label>
            <div class="input-with-toggle">
              <input
                v-model="apiKey"
                :type="showApiKey ? 'text' : 'password'"
                class="form-input"
                placeholder="输入你的 MiMo API Key"
              />
              <button class="toggle-vis" @click="showApiKey = !showApiKey">
                <el-icon v-if="showApiKey"><Hide /></el-icon>
                <el-icon v-else><View /></el-icon>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Base URL</label>
            <input v-model="baseUrl" class="form-input" placeholder="https://token-plan-cn.xiaomimimo.com/v1" />
            <span class="form-hint">TokenPlan 会员专属地址</span>
          </div>

          <div class="form-group">
            <label class="form-label">对话模型</label>
            <input v-model="chatModel" class="form-input form-input-readonly" readonly />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">语音识别</label>
              <input v-model="asrModel" class="form-input form-input-readonly" readonly />
            </div>
            <div class="form-group">
              <label class="form-label">语音合成</label>
              <input v-model="ttsModel" class="form-input form-input-readonly" readonly />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">TTS 音色</label>
            <select v-model="ttsVoice" class="form-input form-select">
              <option v-for="opt in ttsVoiceOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
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
            <label class="form-label">API Key <span class="required">*</span></label>
            <div class="input-with-toggle">
              <input
                v-model="qwenApiKey"
                :type="showQwenApiKey ? 'text' : 'password'"
                class="form-input"
                placeholder="输入你的 Qwen API Key (DASHSCOPE_API_KEY)"
              />
              <button class="toggle-vis" @click="showQwenApiKey = !showQwenApiKey">
                <el-icon v-if="showQwenApiKey"><Hide /></el-icon>
                <el-icon v-else><View /></el-icon>
              </button>
            </div>
            <span class="form-hint">在阿里云百炼平台获取</span>
          </div>

          <div class="form-group">
            <label class="form-label">模型</label>
            <select v-model="qwenModel" class="form-input form-select">
              <option v-for="opt in qwenModelOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">音色</label>
              <select v-model="qwenVoice" class="form-input form-select">
                <option v-for="opt in qwenVoiceOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">地域</label>
              <select v-model="qwenRegion" class="form-input form-select">
                <option value="cn">华北2（北京）</option>
                <option value="intl">新加坡</option>
              </select>
            </div>
          </div>

          <div class="form-tip">
            Qwen-Omni-Realtime 支持实时语音对话，延迟更低
          </div>
        </template>

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
  position: relative;
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

.back-btn {
  position: absolute;
  top: 16px;
  left: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--ink-soft);
  cursor: pointer;
  transition: all var(--transition);
}

.back-btn:hover {
  background: var(--surface-hover);
  color: var(--accent);
  border-color: var(--border-interactive);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* Provider tabs */
.provider-tabs {
  display: flex;
  gap: 8px;
  background: var(--canvas);
  border-radius: 12px;
  padding: 4px;
}

.provider-tab {
  flex: 1;
  padding: 10px 16px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--ink-muted);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-tab.active {
  background: var(--accent);
  color: #fff;
  box-shadow: var(--shadow-button);
}

.provider-tab:hover:not(.active) {
  background: var(--surface-hover);
  color: var(--ink);
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
