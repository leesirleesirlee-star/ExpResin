/**
 * ExpResin 登录会话（auth_v1）。
 * 模块级 reactive 单例（与 session.js 同一模式）：
 * - token 持久化在 localStorage（api.js 直接读取注入 Bearer，避免与本模块循环依赖）；
 * - 启动时经 /auth/me 校验一次（main.js 在挂载前 await，路由守卫据此判定）；
 * - 后端判定令牌失效时 api.js 派发 expresin:unauthorized，由 main.js 统一清会话。
 */

import { computed, reactive } from 'vue'
import { api } from './api.js'

export const AUTH_STORAGE_KEY = 'expresin-auth'

function loadStored() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return { token: '', user: null }
    const parsed = JSON.parse(raw)
    return { token: parsed.token || '', user: parsed.user || null }
  } catch {
    return { token: '', user: null }
  }
}

const stored = loadStored()

export const auth = reactive({
  /** 首次 /auth/me 校验是否结束（main.js 挂载前 await，守卫读取时必为 true） */
  ready: false,
  token: stored.token,
  user: stored.user,
})

export const isLoggedIn = computed(() => Boolean(auth.token && auth.user))
export const isAdmin = computed(() => auth.user?.role === 'admin')

function persist() {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token: auth.token, user: auth.user }))
}

export function clearAuth() {
  auth.token = ''
  auth.user = null
  localStorage.removeItem(AUTH_STORAGE_KEY)
}

/** 应用启动时调用一次：本地 token 仍有效则刷新用户信息，失效（401）则清除。 */
export async function initAuth() {
  if (!auth.token) {
    auth.ready = true
    return
  }
  try {
    const { user } = await api.me()
    auth.user = user
    persist()
  } catch (e) {
    // 仅 401 清会话；离线（status 0）保留本地态，避免后端重启把用户踢出
    if (e.status === 401) clearAuth()
  } finally {
    auth.ready = true
  }
}

export async function login(username, password) {
  const r = await api.login({ username, password })
  auth.token = r.token
  auth.user = r.user
  persist()
  return r.user
}

export async function register(username, password, displayName) {
  const r = await api.register({
    username,
    password,
    display_name: (displayName || '').trim() || undefined,
  })
  auth.token = r.token
  auth.user = r.user
  persist()
  return r.user
}

export async function logout() {
  try {
    await api.logout()
  } catch {
    /* 离线或令牌已失效都按已登出处理 */
  }
  clearAuth()
}

export async function changePassword(oldPassword, newPassword) {
  const r = await api.changePassword({ old_password: oldPassword, new_password: newPassword })
  auth.user = r.user
  persist()
  return r.user
}
