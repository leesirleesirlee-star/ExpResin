import { computed, ref } from 'vue'
import { en } from '../i18n/en.js'

const STORAGE_KEY = 'expresin-locale'

function readLocale() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'zh'
  } catch {
    return 'zh'
  }
}

/** zh | en，全应用共享；写入 localStorage，路由切换与刷新后保持。 */
export const locale = ref(readLocale())

const LOCALE_SWAP_DELAY = 170
const LOCALE_TRANSITION_MS = 480

let pendingLocale = null
let swapTimer = null
let cleanupTimer = null

function syncDocumentLanguage() {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale.value === 'en' ? 'en' : 'zh-CN'
  }
}

function commitLocale(target) {
  locale.value = target
  try {
    localStorage.setItem(STORAGE_KEY, target)
  } catch {
    /* 隐私模式下不可写时仅当前会话生效 */
  }
  syncDocumentLanguage()
}

function canAnimateLocale() {
  if (typeof document === 'undefined' || typeof window === 'undefined') return false
  return !window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
}

/**
 * 先用深色柔焦幕布完全遮住页面，在遮罩内替换语言，再淡出。
 * 不在切换瞬间直接改变整页透明度，避免文字仍然可辨、画面过亮。
 */
function runLocaleTransition(target) {
  const root = document.documentElement
  root.classList.remove('locale-switching')
  // 强制重排，确保连续切换时动画能重新开始。
  void root.offsetWidth
  root.classList.add('locale-switching')

  if (swapTimer !== null) window.clearTimeout(swapTimer)
  if (cleanupTimer !== null) window.clearTimeout(cleanupTimer)

  pendingLocale = target
  swapTimer = window.setTimeout(() => {
    commitLocale(target)
    pendingLocale = null
    swapTimer = null
  }, LOCALE_SWAP_DELAY)

  cleanupTimer = window.setTimeout(() => {
    root.classList.remove('locale-switching')
    cleanupTimer = null
  }, LOCALE_TRANSITION_MS)
}

export function setLocale(next) {
  const target = next === 'en' ? 'en' : 'zh'
  if (target === (pendingLocale ?? locale.value)) {
    if (pendingLocale === null) syncDocumentLanguage()
    return
  }

  if (!canAnimateLocale()) {
    if (swapTimer !== null) window.clearTimeout(swapTimer)
    if (cleanupTimer !== null) window.clearTimeout(cleanupTimer)
    pendingLocale = null
    swapTimer = null
    cleanupTimer = null
    commitLocale(target)
    return
  }

  runLocaleTransition(target)
}

export function hasTranslation(text) {
  return typeof text === 'string' && Object.prototype.hasOwnProperty.call(en, text)
}

export function toggleLocale() {
  setLocale((pendingLocale ?? locale.value) === 'zh' ? 'en' : 'zh')
}

/**
 * 中文原文直接作为词典键：中文模式原样返回，英文模式查 en 词典。
 * 支持 {name} 形式的简单占位符，未收录的文本保持原文作为安全回退。
 */
export function t(text, params) {
  if (text === null || text === undefined) return ''
  let value = String(text)
  if (locale.value === 'en') value = en[value] ?? value
  if (!params) return value
  return value.replace(/\{(\w+)\}/g, (match, key) =>
    params[key] === undefined ? match : String(params[key]),
  )
}

export function useI18n() {
  const isEnglish = computed(() => locale.value === 'en')
  return { locale, isEnglish, setLocale, toggleLocale, t }
}

syncDocumentLanguage()
