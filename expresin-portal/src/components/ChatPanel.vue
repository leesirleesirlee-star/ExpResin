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

      <input
        v-model="draft"
        class="input"
        type="text"
        :placeholder="placeholder"
        aria-label="输入消息"
      />

      <button class="btn btn-primary send" type="submit" :disabled="!draft.trim()">
        发送
      </button>
    </form>

    <p v-if="hint" class="hint muted">{{ hint }}</p>
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
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
}
/* 圆角输入框，聚焦时出现琥珀橙高亮（由 .input:focus + --accent 承接） */
.composer .input {
  flex: 1;
  min-width: 0;
  border-radius: var(--radius-full);
  padding: 0 var(--space-4);
}
.send {
  flex: none;
}

.hint {
  flex: none;
  padding: 0 var(--space-4) var(--space-3);
  font: var(--text-xs);
  line-height: 1.45;
}

@media (max-width: 1024px) {
  .chat {
    border-right: none;
  }
}
</style>