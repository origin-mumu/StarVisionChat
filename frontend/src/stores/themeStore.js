/**
 * 主题状态管理
 * 支持 6 套主题切换
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const THEME_KEY = 'starvisionchat_theme'

const THEMES = [
  { id: 'default', name: '暖白', color: '#E85D2A' },
  { id: 'white', name: '纯灰', color: '#333333' },
  { id: 'dark', name: '深空', color: '#7B9AFF' },
  { id: 'green', name: '薄荷', color: '#4A8C5C' },
  { id: 'blue', name: '浅海', color: '#3B7DD8' },
  { id: 'pink', name: '裸粉', color: '#D4638F' },
]

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref('default')
  const themes = ref(THEMES)

  // 初始化主题
  function init() {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved && THEMES.find(t => t.id === saved)) {
      currentTheme.value = saved
    }
    applyTheme(currentTheme.value)
  }

  // 切换主题
  function setTheme(themeId) {
    if (THEMES.find(t => t.id === themeId)) {
      currentTheme.value = themeId
      applyTheme(themeId)
      localStorage.setItem(THEME_KEY, themeId)
    }
  }

  // 应用主题到 DOM
  function applyTheme(themeId) {
    document.documentElement.setAttribute('data-theme', themeId)
  }

  // 监听主题变化
  watch(currentTheme, (newTheme) => {
    applyTheme(newTheme)
  })

  return {
    currentTheme,
    themes,
    init,
    setTheme,
  }
})
