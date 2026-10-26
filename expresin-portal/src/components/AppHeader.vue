<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'
import { auth, isAdmin, logout } from '../data/auth.js'

const { theme, toggleTheme } = useTheme()
const route = useRoute()
const router = useRouter()

/* 四个主功能收进左侧悬浮导航；辅助资源低频使用，放在第二组。
   图标统一为 20px 线性 SVG，不在模板里重复堆放图形代码。 */
const primaryLinks = [
  {
    to: '/',
    label: '工作台',
    desc: '总览与快捷入口',
    icon: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  },
  {
    to: '/setup',
    label: '新建实验',
    desc: '记录方法与材料',
    icon: 'M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 15h8',
  },
  {
    to: '/recognize',
    label: '数据识别',
    desc: '上传并核对数据',
    icon: 'M4 5h16v14H4zM4 10h16M10 5v14',
  },
  {
    to: '/archive',
    label: '实验档案',
    desc: '追溯与导出',
    icon: 'M4 7h16v13H4zM3 3h18v4H3zM9 11h6',
  },
]
const resourceLinks = [
  {
    to: '/calibration',
    label: '标定曲线',
    icon: 'M4 4v16h16M7 16l4-5 3 3 5-8',
  },
  {
    to: '/api-docs',
    label: 'API 文档',
    icon: 'M7 3h7l4 4v14H7zM14 3v5h5M10 12h5M10 16h5',
  },
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

/* ---- 左侧悬浮导航：精密指针悬停展开，触屏点击展开，键盘聚焦展开 ---- */
const navOpen = ref(false)
const navWrap = ref(null)
const navPanel = ref(null)
const navTrigger = ref(null)
const hoverMedia = window.matchMedia('(hover: hover) and (pointer: fine)')
let navCloseTimer = null

function clearNavCloseTimer() {
  if (navCloseTimer !== null) {
    window.clearTimeout(navCloseTimer)
    navCloseTimer = null
  }
}

function openNav() {
  clearNavCloseTimer()
  navOpen.value = true
  menuOpen.value = false
}

function closeNav() {
  clearNavCloseTimer()
  navOpen.value = false
}

function scheduleNavClose() {
  clearNavCloseTimer()
  /* 给跨越图标与浮层边缘的指针留出缓冲，避免导航闪烁 */
  navCloseTimer = window.setTimeout(closeNav, 140)
}

function onNavEnter() {
  if (hoverMedia.matches) openNav()
}

function onNavLeave() {
  if (hoverMedia.matches) scheduleNavClose()
}

function isInsideNav(target) {
  if (!(target instanceof Node)) return false
  return Boolean(navWrap.value?.contains(target) || navPanel.value?.contains(target))
}

function onNavFocusOut(event) {
  if (isInsideNav(event.relatedTarget)) return
  scheduleNavClose()
}

function dismissNav(restoreFocus = false) {
  /* 先移动焦点再关闭：focusin 会打开导航，顺序反过来会被立即重开 */
  if (restoreFocus) navTrigger.value?.focus()
  closeNav()
}

function toggleNav() {
  if (navOpen.value) closeNav()
  else openNav()
}

/* ---- 用户菜单（auth_v1）：头像首字符 + 下拉（改密 / 数据管理 / 退出） ---- */
const displayName = computed(() => auth.user?.display_name || auth.user?.username || '')
const initial = computed(() => (displayName.value || '?').slice(0, 1).toUpperCase())
const menuOpen = ref(false)
const menuWrap = ref(null)

function onDocumentClick(event) {
  if (menuWrap.value && !menuWrap.value.contains(event.target)) menuOpen.value = false
  if (navOpen.value && !isInsideNav(event.target)) closeNav()
}

function onDocumentKeydown(event) {
  if (event.key !== 'Escape') return
  if (menuOpen.value) menuOpen.value = false
  if (navOpen.value) {
    event.preventDefault()
    dismissNav(true)
  }
}

function toggleMenu() {
  closeNav()
  menuOpen.value = !menuOpen.value
}

function goChangePassword() {
  menuOpen.value = false
  router.push({ name: 'auth', query: { mode: 'change' } })
}

function goAdmin() {
  menuOpen.value = false
  router.push({ name: 'admin' })
}

async function onLogout() {
  menuOpen.value = false
  await logout()
  router.push({ name: 'welcome' })
}

/* 路由来源不限于侧栏点击（浏览器后退、页面按钮等），统一在路由变化后回收 */
watch(() => route.fullPath, closeNav)

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onDocumentKeydown)
})
onBeforeUnmount(() => {
  clearNavCloseTimer()
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onDocumentKeydown)
})
</script>

<template>
  <header class="header">
    <div class="left">
      <div
        ref="navWrap"
        class="brand-nav"
        @mouseenter="onNavEnter"
        @mouseleave="onNavLeave"
        @focusin="openNav"
        @focusout="onNavFocusOut"
      >
        <button
          ref="navTrigger"
          class="brand-wrap"
          type="button"
          aria-label="ExpResin，展开功能导航"
          aria-controls="expresin-side-nav"
          :aria-expanded="navOpen"
          :data-tip="navOpen ? null : '展开功能导航'"
          @click="toggleNav"
        >
          <img class="logo" src="/logo.png" alt="" />
          <span class="brand">ExpResin</span>
        </button>

        <!-- 顶栏的 backdrop-filter 会把 fixed 后代变成以顶栏为包含块；
             传送到 body 后才能获得真正的视口全高，并不受顶栏裁剪。 -->
        <Teleport to="body">
          <Transition name="drawer">
            <aside
              v-if="navOpen"
              id="expresin-side-nav"
              ref="navPanel"
              class="side-nav"
              @mouseenter="onNavEnter"
              @mouseleave="onNavLeave"
              @focusin="openNav"
              @focusout="onNavFocusOut"
            >
            <div class="side-brand">
              <img class="side-logo" src="/logo.png" alt="" />
              <span class="side-brand-copy">
                <strong>ExpResin</strong>
                <small>Portal Jarvis</small>
              </span>
              <button
                class="side-close"
                type="button"
                aria-label="收起功能导航"
                @click="dismissNav(true)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>
            </div>

            <div class="side-scroll">
              <nav class="side-group" aria-label="实验流程导航">
                <p class="side-section">实验流程</p>
                <RouterLink
                  v-for="l in primaryLinks"
                  :key="l.to"
                  :to="l.to"
                  class="side-link"
                  :class="{ 'is-active': isActive(l.to) }"
                  :aria-current="isActive(l.to) ? 'page' : undefined"
                  @click="closeNav"
                >
                  <span class="side-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
                      <path :d="l.icon" />
                    </svg>
                  </span>
                  <span class="side-copy">
                    <span class="side-label">{{ l.label }}</span>
                    <span class="side-desc">{{ l.desc }}</span>
                  </span>
                </RouterLink>
              </nav>

              <nav class="side-group side-group--resources" aria-label="辅助资源">
                <p class="side-section">辅助资源</p>
                <RouterLink
                  v-for="l in resourceLinks"
                  :key="l.to"
                  :to="l.to"
                  class="side-link side-link--compact"
                  :class="{ 'is-active': isActive(l.to) }"
                  :aria-current="isActive(l.to) ? 'page' : undefined"
                  @click="closeNav"
                >
                  <span class="side-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
                      <path :d="l.icon" />
                    </svg>
                  </span>
                  <span class="side-label">{{ l.label }}</span>
                </RouterLink>
              </nav>
            </div>

            <footer class="side-footer">
              <span>Raw 只读 · 全程可追溯</span>
              <kbd title="按 Esc 收起导航">Esc</kbd>
            </footer>
            </aside>
          </Transition>
        </Teleport>
      </div>
    </div>

    <div class="right">
      <button
        class="icon-btn"
        type="button"
        :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'"
        @click="toggleTheme"
      >
        <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      </button>

      <div ref="menuWrap" class="user-menu-wrap">
        <button
          class="avatar avatar-btn"
          type="button"
          :aria-label="`账号菜单：${displayName}`"
          :aria-expanded="menuOpen"
          @click.stop="toggleMenu"
        >
          {{ initial }}
        </button>
        <Transition name="menu">
          <div v-if="menuOpen" class="menu" role="menu">
            <div class="menu-head">
              <span class="menu-name">{{ displayName }}</span>
              <span class="menu-role">{{ isAdmin ? '管理员' : '实验员' }}</span>
            </div>
            <button class="menu-item" type="button" role="menuitem" @click="goChangePassword">
              修改密码
            </button>
            <button v-if="isAdmin" class="menu-item" type="button" role="menuitem" @click="goAdmin">
              数据管理
            </button>
            <button
              class="menu-item menu-item--danger"
              type="button"
              role="menuitem"
              @click="onLogout"
            >
              退出登录
            </button>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  height: var(--topbar-h);
  padding: 0 var(--space-4);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-xs), var(--glass-edge);
  z-index: var(--z-header);
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}
.right {
  gap: var(--space-1);
}

.brand-wrap {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: var(--space-1) var(--space-2);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.brand-wrap:hover {
  background: var(--bg-tertiary);
}

.logo {
  display: block;
  width: 28px;
  height: 28px;
}

.brand {
  font: var(--text-sm);
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* ---- 左侧悬浮导航：覆盖内容而不推动布局；品牌区 / 主流程 / 资源 / 数据承诺 ---- */
.side-nav {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: var(--z-overlay);
  display: flex;
  flex-direction: column;
  width: 264px;
  max-width: calc(100vw - 24px);
  height: 100dvh;
  padding: var(--space-3);
  overflow: hidden;
  border: none;
  border-right: 1px solid var(--border-strong);
  /* 左侧贴合视口；仅右侧上下两角使用完全一致的圆角 */
  border-radius: 0 20px 20px 0;
  background: var(--glass-bg-strong);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  /* 右侧定向投影明确覆盖层级，不让整页变暗，也不推动主内容 */
  box-shadow: 20px 0 56px rgb(0 0 0 / 20%), 4px 0 16px rgb(0 0 0 / 10%);
  color: var(--text-primary);
  transform-origin: left center;
}

.side-brand {
  display: flex;
  align-items: center;
  flex: none;
  gap: 10px;
  min-height: 52px;
  padding: 2px 2px var(--space-3);
}
.side-logo {
  flex: none;
  width: 30px;
  height: 30px;
}
.side-brand-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}
.side-brand-copy strong {
  overflow: hidden;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.015em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-brand-copy small {
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 11px;
  letter-spacing: 0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-close {
  display: grid;
  place-items: center;
  flex: none;
  width: 40px;
  height: 40px;
  padding: 0;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard),
    color var(--duration-fast) var(--ease-standard);
}
.side-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.side-close svg {
  width: 18px;
  height: 18px;
  stroke-width: 1.8;
}

.side-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}
.side-group {
  display: grid;
  gap: var(--space-1);
}
.side-group--resources {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}
.side-section {
  margin: var(--space-2) 10px 6px;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
}

.side-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 56px;
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  text-decoration: none;
  transition: background var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard),
    color var(--duration-fast) var(--ease-standard);
}
.side-link:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.side-link.is-active {
  border-color: var(--border-subtle);
  background: var(--bg-card);
  box-shadow: var(--shadow-xs);
  color: var(--text-primary);
}
.side-link.is-active::before {
  content: '';
  position: absolute;
  top: 13px;
  bottom: 13px;
  left: 0;
  width: 3px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--accent);
}
.side-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 28px;
  height: 28px;
  color: var(--text-tertiary);
  transition: color var(--duration-fast) var(--ease-standard);
}
.side-icon svg {
  width: 19px;
  height: 19px;
  stroke-width: 1.6;
}
.side-link:hover .side-icon,
.side-link.is-active .side-icon {
  color: var(--accent);
}
.side-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.side-label {
  min-width: 0;
  overflow: hidden;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-link.is-active .side-label {
  font-weight: 600;
}
.side-desc {
  min-width: 0;
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-link--compact {
  min-height: 42px;
  padding-top: 4px;
  padding-bottom: 4px;
}
.side-link--compact .side-label {
  font-size: 13px;
}
.side-link--compact.is-active::before {
  top: 9px;
  bottom: 9px;
}

.side-footer {
  display: flex;
  align-items: center;
  flex: none;
  justify-content: space-between;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding: var(--space-3) 6px 2px;
  border-top: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  font-size: 10px;
  line-height: 1.4;
}
.side-footer > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-footer kbd {
  flex: none;
  padding: 2px 5px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font: 10px var(--font-mono);
}

/* 展开：单段弹簧曲线，轻微越过后落位；收回：先向右蓄力，再向左回收。
   只动画 transform / opacity，不引起页面重排；离开期间不截获指针。 */
.drawer-enter-active {
  animation: drawer-in 440ms var(--ease-spring) both;
}
.drawer-leave-active {
  pointer-events: none;
  animation: drawer-out 300ms var(--ease-standard) both;
}
@keyframes drawer-in {
  from {
    opacity: 0;
    transform: translate3d(calc(-100% - 20px), 0, 0) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}
@keyframes drawer-out {
  0% {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
  24% {
    opacity: 1;
    transform: translate3d(8px, 0, 0);
  }
  100% {
    opacity: 0;
    transform: translate3d(calc(-100% - 20px), 0, 0) scale(0.985);
  }
}

.avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  margin-left: var(--space-2);
  border-radius: var(--radius-full);
  background: var(--accent-subtle);
  color: var(--accent);
  font: var(--text-sm);
  font-weight: 600;
}

/* ---- 用户菜单 ---- */
.user-menu-wrap {
  position: relative;
}

.avatar-btn {
  border: none;
  cursor: pointer;
  transition: box-shadow var(--duration-fast) var(--ease-standard);
}
.avatar-btn:hover {
  box-shadow: var(--focus-ring);
}

.menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 168px;
  padding: var(--space-1);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-dropdown, 60);
}

.menu-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-1);
}

.menu-name {
  font: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.menu-role {
  font-size: 12px;
  color: var(--text-tertiary);
}

.menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 34px;
  padding: 0 var(--space-3);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font: var(--text-sm);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}
.menu-item:hover {
  background: var(--bg-tertiary);
}
.menu-item--danger {
  color: var(--error);
}

.menu-enter-active {
  transition: opacity var(--duration-fast) var(--ease-decelerate),
    transform var(--duration-fast) var(--ease-decelerate);
}
.menu-leave-active {
  transition: opacity var(--duration-instant) var(--ease-accelerate);
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 1024px) {
  /* 小屏保留 Logo 作为侧栏开关，仅隐藏品牌文字 */
  .brand {
    display: none;
  }
}

@media (max-width: 480px) {
  .header {
    height: var(--topbar-h-mobile);
  }
  .side-nav {
    max-width: calc(100vw - 16px);
    border-radius: 0 16px 16px 0;
  }
}

/* 矮窗口优先保留全部入口；缩短行高并省略辅助说明，仍不足时仅内部滚动 */
@media (max-height: 620px) {
  .side-brand {
    min-height: 44px;
    padding-bottom: var(--space-2);
  }
  .side-link {
    min-height: 44px;
  }
  .side-desc {
    display: none;
  }
  .side-group--resources {
    margin-top: var(--space-2);
    padding-top: var(--space-2);
  }
  .side-footer {
    margin-top: var(--space-2);
    padding-top: var(--space-2);
  }
}

@media (hover: none) {
  .side-footer kbd {
    display: none;
  }
}
</style>