import { createRouter, createWebHashHistory } from 'vue-router'
import { ref } from 'vue'
import { auth, isAdmin, isLoggedIn } from '../data/auth.js'

/**
 * 页面分工（避免单页堆叠全部功能）：
 *   /welcome       初始欢迎页（未登录入口；bare：无顶栏）
 *   /auth          登录 / 注册 / 修改密码（bare）
 *   /              工作台首页：概览、待办、快捷入口
 *   /setup         实验前：Jarvis 引导 + 初始实验信息
 *   /recognize     实验后：上传 → 识别 → 逐列确认
 *   /archive       实验档案：规范文档检索与调用
 *   /archive/:id   规范文档详情
 *   /admin         管理员：用户与全部实验数据（requiresAdmin）
 *   /api-docs      API 文档（规范第九章）
 *
 * meta 约定：public 免登录；bare 无顶栏全屏；requiresAuth 默认均需登录；
 * requiresAdmin 仅管理员。
 */
const routes = [
  {
    path: '/welcome',
    name: 'welcome',
    component: () => import('../views/WelcomeView.vue'),
    meta: { public: true, bare: true },
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('../views/AuthView.vue'),
    meta: { public: true, bare: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/setup',
    name: 'setup',
    component: () => import('../views/SetupView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/recognize',
    name: 'recognize',
    component: () => import('../views/RecognizeView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/archive',
    name: 'archive',
    component: () => import('../views/ArchiveView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/archive/:id',
    name: 'archive-detail',
    component: () => import('../views/ArchiveDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/api-docs',
    name: 'api-docs',
    component: () => import('../views/ApiDocsView.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

/**
 * 空闲时预热各页面的异步 chunk。
 * 路由组件都是动态 import，首次切换到某页要先拉取 chunk；拉取期间旧页定格、
 * 新页缺位，表现为「点击后卡顿、仍显示前一页内容」。首屏挂载后空闲预热，
 * 后续切换即可立即开始过渡，两个方向手感一致。
 */
export function prefetchViewChunks() {
  import('../views/WelcomeView.vue')
  import('../views/AuthView.vue')
  import('../views/HomeView.vue')
  import('../views/SetupView.vue')
  import('../views/RecognizeView.vue')
  import('../views/ArchiveView.vue')
  import('../views/ArchiveDetailView.vue')
  import('../views/AdminView.vue')
  import('../views/ApiDocsView.vue')
}

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

/* ---- 顶栏切换方向 → 页面过渡方向 ----
   顶栏四项有固定空间顺序，页面滑动方向与导航方向一致才有「动画链接」：
   向右走（索引增大）新页从右滑入、旧页向左滑出；向左走反之。
   详情页 / API 文档视为更深层级（始终在「右」侧）。
   bare 页（欢迎/登录）不参与空间序列，统一淡入淡出。 */
const NAV_ORDER = ['/', '/setup', '/recognize', '/archive']
const navIndex = (path) => {
  const i = NAV_ORDER.indexOf(path)
  return i === -1 ? NAV_ORDER.length : i
}
/** @type {import('vue').Ref<'forward'|'back'|'fade'>} */
export const navDirection = ref('fade')

router.beforeEach((to, from) => {
  /* 过渡方向（原导航动画逻辑） */
  if (to.meta.bare || from.meta.bare) {
    navDirection.value = 'fade'
  } else {
    const ti = navIndex(to.path)
    const fi = navIndex(from.path)
    navDirection.value = ti === fi ? 'fade' : ti > fi ? 'forward' : 'back'
  }

  /* 鉴权守卫（auth_v1）。main.js 在挂载前 await initAuth()，
     此处读取的登录态必是已校验后的结果。 */
  if (to.meta.public) {
    // 已登录用户回到欢迎页没有意义，直接进工作台
    if (to.name === 'welcome' && isLoggedIn.value) return { name: 'home' }
    return true
  }
  if (!isLoggedIn.value) {
    return {
      name: 'welcome',
      query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
    }
  }
  // 种子 admin 等带强制改密标记的账号：改完密码前哪也去不了
  if (auth.user?.must_change_password && to.name !== 'auth') {
    return { name: 'auth', query: { mode: 'change' } }
  }
  if (to.meta.requiresAdmin && !isAdmin.value) return { name: 'home' }
  return true
})

export default router
