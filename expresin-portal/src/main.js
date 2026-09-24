import { createApp } from 'vue'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'
import router from './router/index.js'

createApp(App).use(router).mount('#app')