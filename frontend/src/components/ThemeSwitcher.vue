<template>
  <div class="theme-switcher">
    <div
      v-for="theme in themes"
      :key="theme.id"
      :class="['theme-dot', { active: currentTheme === theme.id }]"
      :style="{ background: theme.color }"
      :data-tooltip="theme.name"
      @click="setTheme(theme.id)"
    />
  </div>
</template>

<script setup>
import { useThemeStore } from '../stores/themeStore'
import { storeToRefs } from 'pinia'

const themeStore = useThemeStore()
const { currentTheme, themes } = storeToRefs(themeStore)
const { setTheme } = themeStore
</script>

<style scoped>
.theme-switcher {
  display: flex;
  gap: 8px;
  align-items: center;
}

.theme-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--transition);
  border: 2px solid transparent;
  position: relative;
}

.theme-dot:hover {
  transform: scale(1.15);
}

.theme-dot.active {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--canvas), 0 0 0 4px var(--ink);
}

/* Tooltip */
.theme-dot::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 8px;
  background: var(--ink);
  color: var(--canvas);
  font-size: 11px;
  border-radius: 4px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
}

.theme-dot:hover::after {
  opacity: 1;
}
</style>
