<script setup>
import { ref, reactive, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'

const { theme, toggleTheme } = useTheme()
const route = useRoute()

const links = [
  { to: '/', label: '工作台' },
  { to: '/setup', label: '新建实验' },
  { to: '/recognize', label: '数据识别' },
  { to: '/archive', label: '实验档案' },
]

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
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
})
onBeforeUnmount(() => window.removeEventListener('resize', updateSlider))
</script>

<template>
  <header class="header">
    <div class="left">
      <RouterLink to="/" class="brand-wrap" data-tip="回到工作台" aria-label="回到工作台">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linejoin="round">
            <path d="M12 3 20 7.5v9L12 21 4 16.5v-9L12 3Z" />
            <path d="M12 12 20 7.5M12 12v9M12 12 4 7.5" />
          </svg>
        </span>
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

      <span class="avatar" aria-hidden="true">J</span>
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
  box-shadow: var(--shadow-xs);
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
/* 悬停提示：「回到工作台」 */
.brand-wrap::after {
  content: attr(data-tip);
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translate(-50%, -2px);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  background: var(--text-primary);
  color: var(--bg-primary);
  font-size: 12px;
  line-height: 1.5;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}
.brand-wrap:hover::after {
  opacity: 1;
  transform: translate(-50%, 0);
}

.logo {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  color: var(--accent);
}
.logo svg {
  width: 24px;
  height: 24px;
  stroke-width: 1.5;
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
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--nav-track);
}

.nav-slider {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 0;
  border-radius: var(--radius-full);
  background: var(--surface-card);
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