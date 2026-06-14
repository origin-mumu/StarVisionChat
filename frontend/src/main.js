import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'highlight.js/styles/atom-one-dark.min.css'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import { useThemeStore } from './stores/themeStore'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(ElementPlus)
app.use(router)

// 初始化主题
const themeStore = useThemeStore()
themeStore.init()

app.mount('#app')
