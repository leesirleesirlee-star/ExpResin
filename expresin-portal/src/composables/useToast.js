import { ref } from 'vue'

/**
 * 轻量 toast 队列。
 * 规范 §4.8：最多同时 3 条；错误信息需要可读、可关闭、停留更久。
 * 兼容旧调用：show(text) / show(text, 4200) / show(text, { tone, duration })
 */
const MAX = 3

const DURATION = {
  success: 3000,
  info: 3400,
  warning: 4600,
  error: 6000,
}

const toasts = ref([])
let seq = 0

function dismiss(id) {
  const i = toasts.value.findIndex((t) => t.id === id)
  if (i !== -1) toasts.value.splice(i, 1)
}

export function useToast() {
  return {
    toasts,
    dismiss,
    show(text, opts = {}) {
      const tone = typeof opts === 'string' ? opts : opts.tone || 'info'
      const duration =
        typeof opts === 'number'
          ? opts
          : opts.duration ?? DURATION[tone] ?? DURATION.info

      const id = ++seq
      toasts.value.push({ id, text: String(text), tone })
      // 超过上限时挤掉最早的一条，保证不遮挡内容
      while (toasts.value.length > MAX) toasts.value.shift()
      if (duration > 0) window.setTimeout(() => dismiss(id), duration)
      return id
    },
  }
}
