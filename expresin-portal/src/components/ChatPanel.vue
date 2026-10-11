<script setup>
import { nextTick, ref, watch } from 'vue'
import PanelHead from './PanelHead.vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  messages: { type: Array, required: true },
  streaming: { type: Boolean, default: false },
  placeholder: { type: String, default: '描述你的实验安排，或提问…' },
  hint: { type: String, default: '' },
  showUpload: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'upload'])

const draft = ref('')
const scroller = ref(null)
const hintOpen = ref(false)

function submit() {
  const text = draft.value.trim()
  if (!text) return
  emit('send', text)
  draft.value = ''
}

watch(
  () => [props.messages.length, props.streaming],
  async () => {
    await nextTick()
    const el = scroller.value
    if (el) el.scrollTop = el.scrollHeight
  },
)
</script>

<template>
  <section class="panel chat" aria-label="Jarvis 对话">
    <PanelHead label="Jarvis" dot>
      <template #actions>
        <span class="badge badge-accent">实验记录助手</span>
      </template>
    </PanelHead>

    <div ref="scroller" class="thread" role="log" aria-live="polite">
      <ChatMessage v-for="(m, i) in messages" :key="m.id ?? i" :message="m" />

      <ChatMessage v-if="streaming" :message="{ role: 'jarvis' }" streaming />
    </div>

    <form class="composer" @submit.prevent="submit">
      <button
        v-if="showUpload"
        class="icon-btn"
        type="button"
        aria-label="上传实验数据文件"
        @click="$emit('upload')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 16V4m0 0L8 8m4-4 4 4" />
          <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
      </button>

      <div class="input-wrap" :class="{ filled: !!draft }">
        <input
          v-model="draft"
          class="input"
          type="text"
          aria-label="输入消息"
        />
        <span class="input-tip" aria-hidden="true">{{ placeholder }}</span>
      </div>

      <button class="send" type="submit" :disabled="!draft.trim()" aria-label="发送">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 19V5m0 0-6 6m6-6 6 6" />
        </svg>
      </button>
    </form>

    <div v-if="hint" class="hintbar">
      <button
        type="button"
        class="hint-trigger"
        :aria-expanded="hintOpen"
        @click="hintOpen = !hintOpen"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4m0-4h.01" />
        </svg>
        提示
      </button>
      <div v-if="hintOpen" class="hint-card" role="note">
        <p>{{ hint }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* Jarvis 温暖对话区：背景与工作台一致，不再使用冷灰系统面板 */
.chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--chat-surface);
  border-right: 1px solid var(--border-subtle);
}


.thread {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.composer {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border-subtle);
}
/* 圆角输入框：比全局 .input（40px）更矮的 36px，聚焦出现琥珀橙高亮 */
.composer .input {
  flex: 1;
  min-width: 0;
  height: 36px;
  border-radius: var(--radius-full);
  padding: 0 var(--space-4);
  font: var(--text-sm);
}
/* 输入区悬浮提示：悬停显示气泡；点击键入（focus-within）或已有内容时消失 */
.input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
}
.input-tip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: var(--space-2);
  z-index: var(--z-toast);
  max-width: 100%;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  background: var(--text-primary);
  color: var(--bg-primary);
  font: var(--text-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0;
  transform: translateY(2px);
  pointer-events: none;
  transition: opacity var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}
.input-wrap:hover .input-tip {
  opacity: 1;
  transform: translateY(0);
}
.input-wrap:focus-within .input-tip,
.input-wrap.filled:hover .input-tip {
  opacity: 0;
}
/* 发送：圆角矩形（squircle）上箭头图标钮，替代原文字按钮 */
.send {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: var(--radius-lg);
  background: var(--accent);
  color: var(--on-accent);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: background var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard),
    opacity var(--duration-fast) var(--ease-standard),
    transform var(--duration-instant) var(--ease-standard);
}
.send:hover:not(:disabled) {
  background: var(--accent-hover);
  box-shadow: var(--shadow-sm);
}
.send:active:not(:disabled) {
  transform: scale(0.92);
}
.send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}
.send svg {
  width: 16px;
  height: 16px;
}

/* 「提示」触发器 + 点击弹出的详细信息卡片 */
.hintbar {
  position: relative;
  flex: none;
  padding: 0 var(--space-4) var(--space-2);
}
.hint-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 1px var(--space-2);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-tertiary);
  font: var(--text-xs);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-standard),
    background var(--duration-fast) var(--ease-standard);
}
.hint-trigger:hover,
.hint-trigger[aria-expanded='true'] {
  color: var(--accent-hover);
  background: var(--accent-subtle);
}
.hint-trigger svg {
  width: 14px;
  height: 14px;
}
.hint-card {
  position: absolute;
  bottom: 100%;
  left: var(--space-4);
  right: var(--space-4);
  z-index: var(--z-toast);
  margin-bottom: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-card);
  box-shadow: var(--shadow-md);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.55;
  animation: hint-pop var(--duration-fast) var(--ease-standard);
}
@keyframes hint-pop {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .chat {
    border-right: none;
  }
}
</style>