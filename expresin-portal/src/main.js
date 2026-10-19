import { createApp } from 'vue'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'
import router, { prefetchViewChunks } from './router/index.js'
import { clearAuth, initAuth } from './data/auth.js'

/* 后端判定令牌失效（过期 / 改密后其他会话被踢）→ 清本地会话并回登录页 */
window.addEventListener('expresin:unauthorized', () => {
  clearAuth()
  if (router.currentRoute.value.name !== 'auth') {
    router.push({ name: 'auth', query: { reason: 'expired' } })
  }
})

/* 先校验本地令牌再挂载：路由守卫读到的是已校验的登录态，
   避免刷新后拿着有效 token 却闪跳欢迎页。 */
initAuth().finally(() => {
  const app = createApp(App).use(router)
  app.mount('#app')

  /* 首屏渲染完成后趁空闲预热其余页面 chunk，保证顶栏切换时过渡立即开始 */
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(prefetchViewChunks, { timeout: 2000 })
  } else {
    window.setTimeout(prefetchViewChunks, 300)
  }
})
