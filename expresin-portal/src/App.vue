<script setup>
import AppHeader from './components/AppHeader.vue'
import { useToast } from './composables/useToast.js'

const { message } = useToast()
</script>

<template>
  <div class="app">
    <AppHeader />
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>

    <Transition name="toast">
      <div v-if="message" class="toast" role="status">{{ message }}</div>
    </Transition>
  </div>
</template>

<style scoped>
.app {
  position: relative;
  display: grid;
  grid-template-rows: var(--topbar-h) minmax(0, 1fr);
  height: 100%;
  background: var(--bg-primary);
  overflow: hidden;
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

.toast {
  position: absolute;
  right: var(--space-5);
  bottom: var(--space-5);
  width: 320px;
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
  font: var(--text-sm);
  z-index: 60;
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

@media (max-width: 640px) {
  .app {
    grid-template-rows: 48px minmax(0, 1fr);
  }
  .toast {
    right: var(--space-4);
    left: var(--space-4);
    width: auto;
  }
}
</style>