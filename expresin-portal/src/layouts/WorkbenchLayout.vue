<script setup>
import { computed, ref } from 'vue'

/**
 * 三栏工作台布局：只服务于真正需要「对话 + 表单 + 检查」的页面。
 * 结构：页面工具条（标题/阶段进度/折叠） + 三栏 + 底部状态栏。
 */
const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  steps: { type: Array, default: () => [] },
  activeStep: { type: String, default: '' },
})

const chatOpen = ref(true)
const inspectorOpen = ref(true)
const tab = ref('form')

/** 当前步骤的下标；-1 表示未知。用于把已走过的步骤标为 is-done。 */
const activeIndex = computed(() => props.steps.findIndex((s) => s.id === props.activeStep))

const tabs = [
  { key: 'chat', label: '对话' },
  { key: 'form', label: '表单' },
  { key: 'inspector', label: '检查' },
]

const style = computed(() => ({
  '--chat-col': chatOpen.value ? 'var(--chat-w)' : 'var(--rail-collapsed-w)',
  '--inspector-col': inspectorOpen.value ? 'var(--inspector-w)' : 'var(--rail-collapsed-w)',
}))
</script>

<template>
  <div class="workbench">
    <header class="workbar">
      <div class="titles">
        <h1 :data-tip="subtitle || null" data-tip-align="start">{{ title }}</h1>
      </div>

      <div v-if="steps.length" class="flow">
        <ol class="steps" aria-label="实验流程进度">
          <li
            v-for="(s, i) in steps"
            :key="s.id"
            :class="{ 'is-active': s.id === activeStep, 'is-done': i < activeIndex }"
            :aria-current="s.id === activeStep ? 'step' : undefined"
          >
            <span class="dot" aria-hidden="true"></span>
            <span>{{ s.label }}</span>
            <span v-if="i < steps.length - 1" class="link" aria-hidden="true"></span>
          </li>
        </ol>
      </div>

      <div class="actions">
        <slot name="actions" />
        <button
          class="icon-btn"
          type="button"
          :aria-pressed="chatOpen"
          aria-label="折叠或展开对话面板"
          @click="chatOpen = !chatOpen"
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
          @click="inspectorOpen = !inspectorOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M15 4v16" />
          </svg>
        </button>
      </div>
    </header>

    <div class="panes" :data-tab="tab" :style="style">
      <div
        id="pane-chat"
        class="pane pane--chat"
        :class="{ 'pane--collapsed': !chatOpen }"
        role="tabpanel"
        aria-labelledby="tab-chat"
      >
        <slot v-if="chatOpen" name="chat" />
        <div v-else class="rail">
          <button
            class="icon-btn"
            type="button"
            aria-label="展开对话面板"
            @click="chatOpen = true"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M9 4v16" />
            </svg>
          </button>
          <span class="rail-label caps">对话</span>
        </div>
      </div>

      <div id="pane-form" class="pane pane--form" role="tabpanel" aria-labelledby="tab-form">
        <slot name="form" />
      </div>

      <div
        id="pane-inspector"
        class="pane pane--inspector"
        :class="{ 'pane--collapsed': !inspectorOpen }"
        role="tabpanel"
        aria-labelledby="tab-inspector"
      >
        <slot v-if="inspectorOpen" name="inspector" />
        <div v-else class="rail">
          <button
            class="icon-btn"
            type="button"
            aria-label="展开检查面板"
            @click="inspectorOpen = true"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <path d="M15 4v16" />
            </svg>
          </button>
          <span class="rail-label caps">检查</span>
        </div>
      </div>
    </div>

    <nav class="tabs" role="tablist" aria-label="面板切换">
      <button
        v-for="t in tabs"
        :key="t.key"
        :id="`tab-${t.key}`"
        type="button"
        role="tab"
        :aria-selected="tab === t.key"
        :aria-controls="`pane-${t.key}`"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
      </button>
    </nav>

    <footer class="status"><slot name="status" /></footer>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  grid-template-rows: var(--panel-head-h) minmax(0, 1fr) 0 minmax(0, auto);
  min-height: 0;
  height: 100%;
  position: relative;
  z-index: var(--z-panel);
}

/* 三列等宽栅格：左右各占 1fr，中列 auto ——
   流程指示因此永远落在工具条正中，不受标题/按钮宽度影响（前后页位置一致） */
.workbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-primary);
}

.titles {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  min-width: 0;
  overflow: hidden;
}
.titles h1 {
  font: var(--text-xl);
  font-weight: 600;
  letter-spacing: var(--tracking-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flow {
  justify-self: center;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.steps {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}
.steps li {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font: var(--text-xs);
  color: var(--text-tertiary);
  white-space: nowrap;
}
.steps .dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: currentColor;
}
/* 步骤之间用细线连起来，表达先后顺序 */
.steps .link {
  width: 14px;
  height: 1px;
  margin-left: var(--space-1);
  background: var(--border-strong);
}
.steps li.is-done {
  color: var(--text-secondary);
}
.steps li.is-active {
  color: var(--accent);
  font-weight: 500;
}

.actions {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.panes {
  display: grid;
  grid-template-columns: var(--chat-col, var(--chat-w)) minmax(0, 1fr) var(--inspector-col, var(--inspector-w));
  gap: var(--space-3);
  padding: var(--space-3);
  min-height: 0;
  transition: grid-template-columns var(--duration-normal) var(--ease-standard);
}
/* 每栏独立成卡片：边框 + 圆角 + 细阴影，栏间以画布灰分隔 */
.pane {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
}
.pane > :deep(*) {
  flex: 1;
  min-width: 0;
}

/* 三列入场：从左到右依次显现 —— 每列轻微左滑 + 淡入，延迟 0/80/160ms，
   与整页交叉淡入叠加出「列级节奏」；只在挂载时播放一次，不影响折叠的 grid 过渡 */
@media (prefers-reduced-motion: no-preference) {
  .pane--chat {
    animation: pane-in var(--duration-normal) var(--ease-decelerate) both;
  }
  .pane--form {
    animation: pane-in var(--duration-normal) var(--ease-decelerate) 80ms both;
  }
  .pane--inspector {
    animation: pane-in var(--duration-normal) var(--ease-decelerate) 160ms both;
  }
}
@keyframes pane-in {
  from {
    opacity: 0;
    transform: translateX(-16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 折叠态：保留 48px 图标条，而不是整栏消失（规范 §3.3 / changelog §2）。
   轨道与工作台同色系（暖米/暖炭），去阴影使其后退为「框架」而非白色卡片 */
.pane--collapsed {
  align-items: center;
  background: var(--bg-workbench);
  box-shadow: none;
}
.rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  width: 100%;
}
.rail-label {
  writing-mode: vertical-rl;
  letter-spacing: var(--tracking-caps);
  color: var(--text-secondary);
}

.tabs {
  display: none;
}

.status {
  min-height: 0;
}

@media (max-width: 1024px) {
  .workbench {
    grid-template-rows: var(--panel-head-h) minmax(0, 1fr) 52px auto;
  }
  .panes {
    grid-template-columns: minmax(0, 1fr);
  }
  .pane {
    display: none;
  }
  .panes[data-tab='chat'] .pane--chat,
  .panes[data-tab='form'] .pane--form,
  .panes[data-tab='inspector'] .pane--inspector {
    display: flex;
  }
  .flow {
    display: none;
  }
  .tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-secondary);
  }
  .tabs button {
    border: none;
    background: transparent;
    font: var(--text-sm);
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    min-height: 44px;
    transition: background var(--duration-fast) var(--ease-standard),
      color var(--duration-fast) var(--ease-standard);
  }
  .tabs button:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }
  .tabs button.active {
    color: var(--accent);
    box-shadow: inset 0 -2px 0 var(--accent);
  }
}
</style>