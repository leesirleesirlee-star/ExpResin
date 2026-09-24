<script setup>
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
</script>

<template>
  <header class="header">
    <div class="left">
      <RouterLink to="/" class="brand-wrap">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linejoin="round">
            <path d="M12 3 20 7.5v9L12 21 4 16.5v-9L12 3Z" />
            <path d="M12 12 20 7.5M12 12v9M12 12 4 7.5" />
          </svg>
        </span>
        <span class="brand">ExpResin</span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
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
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-xs);
  z-index: 30;
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

.nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-4);
}

.nav-link {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  font: var(--text-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: background var(--duration-fast) var(--ease-standard),
    color var(--duration-fast) var(--ease-standard);
}
.nav-link:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
.nav-link.is-active {
  background: var(--accent-subtle);
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

@media (max-width: 900px) {
  .brand,
  .docs {
    display: none;
  }
  .nav {
    margin-left: var(--space-2);
  }
}

@media (max-width: 640px) {
  .header {
    height: 48px;
  }
  .nav-link {
    padding: 0 var(--space-2);
    font-size: 13px;
  }
}
</style>