<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'
import { auth, isAdmin, logout } from '../data/auth.js'

const { theme, toggleTheme } = useTheme()
const route = useRoute()
const router = useRouter()

const links = [
  { to: '/', label: '工作台' },
  { to: '/setup', label: '新建实验' },
  { to: '/recognize', label: '数据识别' },
  { to: '/archive', label: '实验档案' },
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

/* ---- 用户菜单（auth_v1）：头像首字符 + 下拉（改密 / 数据管理 / 退出） ---- */
const displayName = computed(() => auth.user?.display_name || auth.user?.username || '')
const initial = computed(() => (displayName.value || '?').slice(0, 1).toUpperCase())
const menuOpen = ref(false)
const menuWrap = ref(null)

function closeMenuOnOutside(e) {
  if (menuWrap.value && !menuWrap.value.contains(e.target)) menuOpen.value = false
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

/* 分段控件滑块：测量激活链接的位置与宽度，transform 平移过去 */
const navEl = ref(null)
const slider = reactive({ x: 0, w: 0, ready: false })

async function updateSlider() {
  await nextTick()
  const nav = navEl.value
  if (!nav) return
  const active = nav.querySelector('.nav-link.is-active')
  if (!active) {
    slider.ready = false
    return
  }
  slider.x = active.offsetLeft
  slider.w = active.offsetWidth
  slider.ready = true
}

watch(() => route.path, updateSlider)
onMounted(() => {
  updateSlider()
  window.addEventListener('resize', updateSlider)
  document.addEventListener('click', closeMenuOnOutside)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateSlider)
  document.removeEventListener('click', closeMenuOnOutside)
})
</script>

<template>
  <header class="header">
    <div class="left">
      <RouterLink to="/" class="brand-wrap" data-tip="回到工作台" aria-label="回到工作台">
        <img class="logo" src="/logo.png" alt="" />
        <span class="brand">ExpResin</span>
      </RouterLink>

      <nav ref="navEl" class="nav" aria-label="主导航">
        <span
          class="nav-slider"
          aria-hidden="true"
          :style="{
            transform: `translateX(${slider.x}px)`,
            width: `${slider.w}px`,
            opacity: slider.ready ? 1 : 0,
          }"
        ></span>
        <RouterLink
          v-for="l in links"
          :key="l.to"
          :to="l.to"
          class="nav-link"
          :class="{ 'is-active': isActive(l.to) }"
        >
          {{ l.label }}
        </RouterLink>
      </nav>
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

      <RouterLink to="/api-docs" class="btn btn-ghost docs">API Docs</RouterLink>

      <div ref="menuWrap" class="user-menu-wrap">
        <button
          class="avatar avatar-btn"
          type="button"
          :aria-label="`账号菜单：${displayName}`"
          :aria-expanded="menuOpen"
          @click.stop="menuOpen = !menuOpen"
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
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  text-decoration: none;
  color: inherit;
}
.brand-wrap:hover {
  background: var(--bg-tertiary);
}
/* 「回到工作台」悬停提示由 base.css 的全局 [data-tip] 工具承接 */

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

/* 分段控件：圆角矩形轨道以 --nav-track 与顶栏拉开对比，滑块在激活项之间快速平移 */
.nav {
  position: relative;
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: var(--space-4);
  padding: 4px;
  border: 1px solid var(--nav-track-border);
  border-radius: var(--radius-full);
  background: var(--nav-track);
}

.nav-slider {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 0;
  border-radius: var(--radius-full);
  background: var(--nav-slider);
  box-shadow: var(--shadow-sm);
  pointer-events: none;
  transition: transform var(--duration-fast) var(--ease-standard),
    width var(--duration-fast) var(--ease-standard),
    opacity var(--duration-fast) var(--ease-standard);
}

.nav-link {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-full);
  font: var(--text-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-standard);
}
.nav-link:hover {
  color: var(--text-primary);
}
.nav-link.is-active {
  color: var(--accent);
  font-weight: 500;
}

.docs {
  text-decoration: none;
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
  .brand,
  .docs {
    display: none;
  }
  .nav {
    margin-left: var(--space-2);
  }
}

@media (max-width: 480px) {
  .header {
    height: var(--topbar-h-mobile);
  }
  .nav-link {
    padding: 0 var(--space-2);
    font-size: 13px;
  }
}
</style>