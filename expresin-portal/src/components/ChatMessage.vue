<script setup>
/**
 * 对话消息气泡（升级方案 §7.1）。
 *
 * 取代 ChatPanel 内联的消息模板，统一 user / jarvis / error 三态：
 *  - 错误消息用独立样式并以 role="alert" 播报，不再与普通回复同形；
 *  - 长文本 pre-wrap + break-word，代码/表格内容不被截断；
 *  - chips 作为消息附带的候选/标签。
 */
const props = defineProps({
  /** { role, content|text, chips } */
  message: { type: Object, required: true },
  /** 流式输出中：渲染打字指示气泡而非文本 */
  streaming: { type: Boolean, default: false },
})

function textOf(m) {
  return m.content ?? m.text ?? ''
}
</script>

<template>
  <article
    class="msg enter-up"
    :class="`msg--${props.message.role === 'user' ? 'user' : props.message.role === 'error' ? 'error' : 'jarvis'}`"
    :role="props.message.role === 'error' ? 'alert' : undefined"
  >
    <p v-if="streaming" class="bubble typing" aria-label="Jarvis 正在输入">
      <i></i><i></i><i></i>
    </p>
    <template v-else>
      <p class="bubble">{{ textOf(props.message) }}</p>
      <div v-if="props.message.chips?.length" class="chips">
        <span v-for="c in props.message.chips" :key="c" class="badge badge-neutral">{{ c }}</span>
      </div>
    </template>
  </article>
</template>

<style scoped>
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
.msg--error .bubble {
  background: var(--error-bg);
  color: var(--error);
  border-left: 2px solid var(--error);
  border-top-left-radius: var(--radius-sm);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-left: var(--space-1);
}
</style>
