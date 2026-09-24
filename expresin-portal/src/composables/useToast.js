import { ref } from 'vue'

const message = ref('')
let timer = null

export function useToast() {
  return {
    message,
    show(text, ms = 4200) {
      message.value = text
      window.clearTimeout(timer)
      timer = window.setTimeout(() => (message.value = ''), ms)
    },
  }
}