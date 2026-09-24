import { createRouter, createWebHashHistory } from 'vue-router'

/**
 * 页面分工（避免单页堆叠全部功能）：
 *   /              工作台首页：概览、待办、快捷入口
 *   /setup         实验前：Jarvis 引导 + 初始实验信息
 *   /recognize     实验后：上传 → 识别 → 逐列确认
 *   /archive       实验档案：规范文档检索与调用
 *   /archive/:id   规范文档详情
 *   /api-docs      API 文档（规范第九章）
 */
const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/setup', name: 'setup', component: () => import('../views/SetupView.vue') },
  { path: '/recognize', name: 'recognize', component: () => import('../views/RecognizeView.vue') },
  { path: '/archive', name: 'archive', component: () => import('../views/ArchiveView.vue') },
  {
    path: '/archive/:id',
    name: 'archive-detail',
    component: () => import('../views/ArchiveDetailView.vue'),
  },
  { path: '/api-docs', name: 'api-docs', component: () => import('../views/ApiDocsView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})