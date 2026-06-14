import { createRouter, createWebHashHistory } from 'vue-router'
import CoverPage from '../components/CoverPage.vue'
import ConfigPage from '../components/ConfigPage.vue'
import ImmersiveChat from '../components/ImmersiveChat.vue'
import RemoteCamera from '../views/RemoteCamera.vue'

const routes = [
  { path: '/', name: 'cover', component: CoverPage },
  { path: '/config', name: 'config', component: ConfigPage },
  { path: '/chat', name: 'chat', component: ImmersiveChat },
  { path: '/camera', name: 'camera', component: RemoteCamera },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

/**
 * 路由守卫：已配置用户自动跳过封面和配置页
 */
router.beforeEach((to, from) => {
  // 从入口首次进入首页时，检查是否已配置
  if (to.name === 'cover' && !from.name) {
    const saved = localStorage.getItem('starvisionchat_config')
    if (saved) {
      try {
        const config = JSON.parse(saved)
        if (config.configured && config.apiKey) {
          return { name: 'chat' }
        }
      } catch { /* ignore */ }
    }
  }
  return true
})

export default router
