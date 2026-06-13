<template>
  <CoverPage v-if="stage === 'cover'" @enter="onCoverEnter" />
  <ConfigPage v-else-if="stage === 'config'" @done="onConfigDone" />
  <ImmersiveChat v-else />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import CoverPage from './components/CoverPage.vue'
import ConfigPage from './components/ConfigPage.vue'
import ImmersiveChat from './components/ImmersiveChat.vue'
import { wsService } from './services/wsService'
import { useChatStore } from './stores/chatStore'
import { useThemeStore } from './stores/themeStore'

const chatStore = useChatStore()
const themeStore = useThemeStore()

// Flow: cover → config → main
const stage = ref('cover')

function onCoverEnter() {
  // If already configured, skip config page
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      if (config.configured && config.apiKey) {
        stage.value = 'main'
        return
      }
    } catch { /* ignore */ }
  }
  stage.value = 'config'
}

function onConfigDone() {
  stage.value = 'main'
}

onMounted(() => {
  themeStore.init()

  // Check if returning user (already configured) → skip cover
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      if (config.configured && config.apiKey) {
        stage.value = 'main'
      }
    } catch { /* ignore */ }
  }

  // Connect WebSocket
  wsService.connect()
  wsService.on('connected', () => { chatStore.isConnected = true })
  wsService.on('disconnected', () => { chatStore.isConnected = false })
  wsService.on('status', (data) => { chatStore.setStatus(data.status, data.message) })
  wsService.on('cost_update', (data) => { chatStore.updateCost(data) })
})

onUnmounted(() => { wsService.disconnect() })
</script>
