<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import { useToast } from './composables/useToast.js'
import { navDirection } from './router/index.js'

const { toasts, dismiss } = useToast()
const route = useRoute()

/* bare 路由（欢迎页 / 登录页）：无顶栏的全屏页，App.vue 网格也要让出顶栏行 */
const bare = computed(() => Boolean(route.meta.bare))

/* 页面过渡名跟随导航方向：顶栏右移 → page-right（新页从右入），
   左移 → page-left（新页从左入），同级/未知 → page-fade（纯淡入淡出），
   向导步骤组内互切（新建实验 ↔ 数据识别）→ page-none（零位移，步骤条固定）。
   滑动方向与顶栏指示条一致，形成「动画链接」。 */
const transitionName = computed(() =>
  navDirection.value === 'forward'
    ? 'page-right'
    : navDirection.value === 'back'
      ? 'page-left'
      : navDirection.value === 'none'
        ? 'page-none'
        : 'page-fade',
)
</script>

<template>
  <div class="app" :class="{ 'app--bare': bare }">
    <AppHeader v-if="!bare" />
    <router-view v-slot="{ Component, route }">
      <!-- 默认模式（新旧页同时过渡）：新页挂载不依赖旧页 afterLeave，
           避免 out-in 在含 Teleport/Modal 的页面上交换子节点时死锁导致整页空白。
           过渡类落在 .page-stage 包装层而非视图根元素：视图 scoped 样式
           （如 .page { position: relative }）曾覆盖 leave-active 的 absolute
           定位，旧页滞留文档流把新页挤到网格外，旧页移除时新页突然上跳；
           包装层样式由全局 base.css 控制，视图无法意外覆盖。 -->
      <Transition :name="transitionName">
        <div :key="route.path" class="page-stage">
          <component :is="Component" />
        </div>
      </Transition>
    </router-view>

    <TransitionGroup name="toast" tag="div" class="toast-stack">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :class="`toast--${t.tone}`"
        :role="t.tone === 'error' ? 'alert' : 'status'"
      >
        <span class="toast-dot" aria-hidden="true"></span>
        <p class="toast-text">{{ t.text }}</p>
        <button class="toast-close" type="button" aria-label="关闭提示" @click="dismiss(t.id)">
          ×
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.app {
  position: relative;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  height: 100%;
  background: var(--bg-canvas);
  overflow: hidden;
}

/* bare 页（欢迎/登录）无顶栏，网格让出第一行 */
.app--bare {
  grid-template-rows: minmax(0, 1fr);
}

/* 5.1 允许的微妙径向渐变，透明度 ≤ 0.1 */
.app::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(60% 50% at 15% 0%, var(--accent-bg), transparent 70%),
    radial-gradient(50% 40% at 100% 100%, var(--accent-bg), transparent 70%);
  opacity: 0.5;
  z-index: 0;
}

.toast-stack {
  position: absolute;
  right: var(--space-5);
  bottom: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 340px;
  max-width: calc(100vw - var(--space-5) * 2);
  z-index: var(--z-toast);
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
  font: var(--text-sm);
}
.toast-dot {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: var(--radius-full);
  background: var(--text-tertiary);
}
.toast-text {
  flex: 1;
  min-width: 0;
  margin: 0;
  line-height: 1.45;
  word-break: break-word;
}
.toast-close {
  flex: none;
  width: 24px;
  height: 24px;
  margin: -2px -4px 0 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
.toast-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.toast--success {
  border-left-color: var(--success);
}
.toast--success .toast-dot {
  background: var(--success);
}
.toast--warning {
  border-left-color: var(--warning);
}
.toast--warning .toast-dot {
  background: var(--warning);
}
.toast--error {
  border-left-color: var(--error);
}
.toast--error .toast-dot {
  background: var(--error);
}
.toast--info .toast-dot {
  background: var(--info);
}

.toast-enter-active {
  transition: all var(--duration-normal) var(--ease-decelerate);
}
.toast-leave-active {
  transition: all var(--duration-fast) var(--ease-accelerate);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

@media (max-width: 480px) {
  .app:not(.app--bare) {
    grid-template-rows: var(--topbar-h-mobile) minmax(0, 1fr);
  }
  .toast-stack {
    right: var(--space-4);
    left: var(--space-4);
    width: auto;
  }
}
</style>
