<script setup>
defineProps({
  project: { type: String, required: true },
  sheets: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: 0 },
  theme: { type: String, required: true },
  chatOpen: { type: Boolean, default: true },
  inspectorOpen: { type: Boolean, default: true },
})

defineEmits(['toggle-theme', 'toggle-chat', 'toggle-inspector', 'select-experiment'])
</script>

<template>
  <header class="topbar">
    <div class="side">
      <span class="logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linejoin="round">
          <path d="M12 3 20 7.5v9L12 21 4 16.5v-9L12 3Z" />
          <path d="M12 12 20 7.5M12 12v9M12 12 4 7.5" />
        </svg>
      </span>
      <span class="brand">ExpResin</span>
    </div>

    <div class="center">
      <span class="caps">Project</span>
      <span class="project-name">{{ project }}</span>

      <span class="sep" aria-hidden="true">/</span>

      <select
        v-if="sheets.length > 1"
        class="sheet"
        :value="activeIndex"
        aria-label="选择要处理的 Sheet"
        @change="$emit('select-experiment', Number($event.target.value))"
      >
        <option v-for="(s, i) in sheets" :key="s.id" :value="i">{{ s.sheet }}</option>
      </select>
      <span v-else-if="sheets.length === 1" class="sheet-static mono">{{ sheets[0].sheet }}</span>
    </div>

    <div class="side right">
      <button
        class="icon-btn"
        type="button"
        :aria-pressed="chatOpen"
        aria-label="折叠或展开对话面板"
        @click="$emit('toggle-chat')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M9 4v16" />
        </svg>
      </button>

      <button
        class="icon-btn"
        type="button"
        :aria-pressed="inspectorOpen"
        aria-label="折叠或展开检查面板"
        @click="$emit('toggle-inspector')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M15 4v16" />
        </svg>
      </button>

      <button
        class="icon-btn"
        type="button"
        :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'"
        @click="$emit('toggle-theme')"
      >
        <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      </button>

      <a class="btn btn-ghost docs" href="#/api-docs">API Docs</a>

      <span class="avatar" aria-hidden="true">J</span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
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
  z-index: 20;
}

.side {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  flex: 1;
}
.right {
  gap: var(--space-1);
  justify-content: flex-end;
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

.center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-width: 0;
  flex: 2;
}

.project-name {
  font: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
}
.sep {
  color: var(--text-tertiary);
}

.sheet {
  height: 32px;
  max-width: 220px;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  font: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-standard);
}
.sheet:hover {
  border-color: var(--accent);
}
.sheet-static {
  font-size: 13px;
  color: var(--text-secondary);
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
  .center .caps {
    display: none;
  }
}

@media (max-width: 640px) {
  .topbar {
    height: 48px;
  }
  .project-name,
  .sep {
    display: none;
  }
}
</style>