<script setup>
import { useI18n } from '../composables/useI18n.js'

const { locale, setLocale, t } = useI18n()
</script>

<template>
  <div
    class="locale-switch"
    :class="{ 'is-en': locale === 'en' }"
    role="group"
    :aria-label="t('切换语言')"
  >
    <span class="locale-thumb" aria-hidden="true" />
    <button
      type="button"
      class="locale-option"
      :class="{ 'is-active': locale === 'zh' }"
      :aria-pressed="locale === 'zh'"
      :title="t('切换到中文')"
      @click="setLocale('zh')"
    >
      中文
    </button>
    <button
      type="button"
      class="locale-option"
      :class="{ 'is-active': locale === 'en' }"
      :aria-pressed="locale === 'en'"
      :title="t('切换到英文')"
      @click="setLocale('en')"
    >
      EN
    </button>
  </div>
</template>

<style scoped>
.locale-switch {
  position: relative;
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  box-sizing: border-box;
  width: 88px;
  height: 34px;
  padding: 2px;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--glass-edge);
}
.locale-thumb {
  position: absolute;
  top: 2px;
  bottom: 2px;
  left: 2px;
  width: calc(50% - 2px);
  border-radius: var(--radius-full);
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  pointer-events: none;
  transform: translateX(0);
  transition: transform 280ms cubic-bezier(0.22, 1, 0.36, 1);
}
.locale-switch.is-en .locale-thumb {
  transform: translateX(100%);
}
.locale-option {
  position: relative;
  z-index: 1;
  min-width: 0;
  height: 28px;
  padding: 0 4px;
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-tertiary);
  font: var(--text-xs);
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: color 180ms var(--ease-standard);
}
.locale-option:hover {
  color: var(--text-primary);
}
.locale-option.is-active {
  color: var(--text-primary);
}
.locale-option:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px var(--accent);
}
@media (prefers-reduced-motion: reduce) {
  .locale-thumb {
    transition: none;
  }
}
</style>
