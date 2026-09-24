import { ref } from 'vue'

const KEY = 'expresin-theme'
const theme = ref(localStorage.getItem(KEY) || 'light')

function apply(value) {
  document.documentElement.dataset.theme = value
  localStorage.setItem(KEY, value)
}
apply(theme.value)

export function useTheme() {
  return {
    theme,
    toggleTheme() {
      theme.value = theme.value === 'dark' ? 'light' : 'dark'
      apply(theme.value)
    },
  }
}