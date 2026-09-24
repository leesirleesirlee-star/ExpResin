<script setup>
import { nextTick, ref, watch } from 'vue'

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

function textOf(m) {
  return m.content ?? m.text ?? ''
}

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
    <div class="panel-head">
      <span class="caps">Jarvis</span>
      <span class="badge badge-accent">实验记录助手</span>
    </div>

    <div ref="scroller" class="thread" role="log" aria-live="polite">
      <article
        v-for="(m, i) in messages"
        :key="m.id ?? i"
        class="msg enter-up"
        :class="m.role === 'user' ? 'msg--user' : 'msg--jarvis'"
      >
        <p class="bubble">{{ textOf(m) }}</p>
        <div v-if="m.chips?.length" class="chips">
          <span v-for="c in m.chips" :key="c" class="badge badge-neutral">{{ c }}</span>
        </div>
      </article>

      <div v-if="streaming" class="msg msg--jarvis">
        <p class="bubble typing" aria-label="Jarvis 正在输入">
          <i></i><i></i><i></i>
        </p>
      </div>
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
.chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-subtle);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
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

.msg {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 100%;
}
.msg--user {
  align-items: flex-end;
}

.bubble {
  max-width: 80%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  font: var(--text-base);
  white-space: pre-wrap;
  word-break: break-word;
}
.msg--jarvis .bubble {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border-top-left-radius: var(--radius-sm);
}
.msg--user .bubble {
  background: var(--accent);
  color: var(--on-accent);
  border-top-right-radius: var(--radius-sm);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-left: var(--space-1);
}

.composer {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
}
.composer .input {
  flex: 1;
  min-width: 0;
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