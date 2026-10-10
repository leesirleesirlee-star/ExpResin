<script setup>
/**
 * 模态对话框（规范 §4.9）。
 *
 * 遮罩 --overlay + blur(8px)，容器背景 --surface-card、最大 560px、--radius-xl、--shadow-lg，
 * 入场 scale(0.96)→1 + 淡入。关闭方式：Esc、点击遮罩、关闭按钮。
 * 打开时把焦点移入对话框，关闭后归还触发元素。
 */
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  /** 容器最大宽度，默认对齐规范 560px */
  maxWidth: { type: String, default: '560px' },
})
const emit = defineEmits(['close'])

const panel = ref(null)
let lastActive = null

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      lastActive = document.activeElement
      document.addEventListener('keydown', onKeydown)
      await nextTick()
      const focusable = panel.value?.querySelector(
        '[autofocus],button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])',
      )
      ;(focusable || panel.value)?.focus()
    } else {
      document.removeEventListener('keydown', onKeydown)
      lastActive?.focus?.()
    }
  },
)

onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
      <div
        ref="panel"
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        :style="{ '--modal-w': maxWidth }"
        tabindex="-1"
      >
        <header class="modal-head">
          <h2>{{ title }}</h2>
          <button class="icon-btn" type="button" aria-label="关闭对话框" @click="emit('close')">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M18 6 6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </header>

        <div class="modal-body">
          <slot />
        </div>

        <footer v-if="$slots.footer" class="modal-foot">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay);
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: var(--overlay);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.modal {
  width: 100%;
  max-width: var(--modal-w, 560px);
  max-height: calc(100vh - var(--space-8));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  animation: modal-in var(--duration-normal) var(--ease-decelerate) both;
}
@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}
.modal-head h2 {
  font: var(--text-lg);
  font-weight: 600;
}
.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
  min-height: 0;
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-subtle);
}
</style>
