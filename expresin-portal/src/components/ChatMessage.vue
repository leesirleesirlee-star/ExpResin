<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from '../composables/useI18n.js'
import { localizeJarvisText } from '../i18n/messages.js'

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
  /** 仅最新的 Jarvis 回复启用快速逐字显示 */
  typewriter: { type: Boolean, default: false },
})

const emit = defineEmits(['progress'])

const { locale } = useI18n()

function textOf(m) {
  return m.content ?? m.text ?? ''
}

const fullText = computed(() => {
  locale.value
  const raw = textOf(props.message)
  if (props.message.role === 'user' || props.message.role === 'error') return raw
  return localizeJarvisText(raw, props.message.params)
})
const displayed = ref('')
const typing = ref(false)
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
let timer = null
let characters = []
let characterIndex = 0
let chunkSize = 2
let lastLocale = locale.value

function stopTimer() {
  if (timer !== null) window.clearTimeout(timer)
  timer = null
}

function typeNext() {
  characterIndex = Math.min(characterIndex + chunkSize, characters.length)
  displayed.value = characters.slice(0, characterIndex).join('')
  emit('progress')

  if (characterIndex >= characters.length) {
    typing.value = false
    timer = null
    return
  }
  /* 比欢迎页 55–115ms 更快；长回复自动增加每帧字符数，避免等待过久。 */
  timer = window.setTimeout(typeNext, 16 + Math.random() * 10)
}

function syncDisplay() {
  stopTimer()
  const localeChanged = locale.value !== lastLocale
  lastLocale = locale.value
  const canType =
    props.typewriter &&
    !props.streaming &&
    !reducedMotion &&
    !localeChanged &&
    props.message.role !== 'user' &&
    props.message.role !== 'error'

  displayed.value = fullText.value
  typing.value = false
  if (!canType || !fullText.value) return

  characters = Array.from(fullText.value)
  characterIndex = 0
  chunkSize = Math.max(2, Math.ceil(characters.length / 160))
  displayed.value = ''
  typing.value = true
  typeNext()
}

watch(
  () => [fullText.value, props.typewriter, props.streaming],
  syncDisplay,
  { immediate: true },
)

onBeforeUnmount(stopTimer)
</script>

<template>
  <article
    class="msg enter-up"
    :class="`msg--${props.message.role === 'user' ? 'user' : props.message.role === 'error' ? 'error' : 'jarvis'}`"
    :role="props.message.role === 'error' ? 'alert' : undefined"
  >
    <p v-if="streaming" class="bubble typing" :aria-label="$t('Jarvis 正在输入')">
      <i></i><i></i><i></i>
    </p>
    <template v-else>
      <p class="bubble" :aria-label="typing ? fullText : undefined">
        <span :aria-hidden="typing ? 'true' : undefined">{{ displayed }}</span><span
          v-if="typing"
          class="type-caret"
          aria-hidden="true"
        ></span>
      </p>
      <div v-if="!typing && props.message.chips?.length" class="chips">
        <span v-for="c in props.message.chips" :key="c" class="badge badge-neutral">{{ $t(c) }}</span>
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
  /* Jarvis 回复无气泡：直接平铺在对话页面上 */
  max-width: 100%;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--text-primary);
  line-height: 1.65;
}
.msg--user .bubble {
  background: var(--chat-bubble);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  border-top-right-radius: var(--radius-sm);
}
.msg--error .bubble {
  background: var(--error-bg);
  color: var(--error);
  border-left: 2px solid var(--error);
  border-top-left-radius: var(--radius-sm);
}
.type-caret {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 3px;
  border-radius: var(--radius-full);
  background: var(--accent);
  vertical-align: -0.12em;
  animation: type-caret-blink 720ms step-end infinite;
}
@keyframes type-caret-blink {
  0%, 45% { opacity: 1; }
  46%, 100% { opacity: 0; }
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-left: var(--space-1);
}
</style>
