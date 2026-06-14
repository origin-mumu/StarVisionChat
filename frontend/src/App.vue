<template>
  <router-view />
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { wsService } from './services/wsService'
import { useChatStore } from './stores/chatStore'

const chatStore = useChatStore()

onMounted(() => {
  wsService.connect()
  wsService.on('connected', () => { chatStore.isConnected = true })
  wsService.on('disconnected', () => { chatStore.isConnected = false })
  wsService.on('status', (data) => { chatStore.setStatus(data.status, data.message) })
  wsService.on('cost_update', (data) => { chatStore.updateCost(data) })
})

onUnmounted(() => { wsService.disconnect() })
</script>
