import { computed, ref } from 'vue'

/**
 * 主题：显式 light / dark，或 auto 跟随系统（默认）。
 * 实现规范 §8.7「跟随系统」——当用户未显式选择时，不写 data-theme，
 * 由 tokens.css 的 prefers-color-scheme 规则接管；显式选择时写 data-theme。
 */
const KEY = 'expresin-theme'

function readSaved() {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'light' || v === 'dark' ? v : 'auto'
  } catch {
    return 'auto'
  }
}

const mq =
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-color-scheme: dark)')
    : null

const mode = ref(readSaved()) // 'auto' | 'light' | 'dark'
const systemDark = ref(mq ? mq.matches : false)

if (mq) {
  const onChange = (e) => {
    systemDark.value = e.matches
  }
  if (mq.addEventListener) mq.addEventListener('change', onChange)
  else if (mq.addListener) mq.addListener(onChange)
}

const theme = computed(() =>
  mode.value === 'auto' ? (systemDark.value ? 'dark' : 'light') : mode.value,
)

function apply() {
  const el = document.documentElement
  if (mode.value === 'auto') el.removeAttribute('data-theme')
  else el.dataset.theme = mode.value
  try {
    localStorage.setItem(KEY, mode.value)
  } catch {
    /* 隐私模式下不可写，忽略 */
  }
}

apply()

export function useTheme() {
  return {
    /** 当前实际生效的主题：'light' | 'dark' */
    theme,
    /** 用户选择：'auto' | 'light' | 'dark' */
    mode,
    /** 在 light / dark 间切换（切换后为显式选择） */
    toggleTheme() {
      mode.value = theme.value === 'dark' ? 'light' : 'dark'
      apply()
    },
    /** 显式设置，传 'auto' 可恢复跟随系统 */
    setMode(next) {
      mode.value = next === 'light' || next === 'dark' ? next : 'auto'
      apply()
    },
  }
}
