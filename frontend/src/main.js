import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import './assets/main.css'
import App from './App.vue'
import router from './router'
import api, { setUnauthorizedHandler } from './api'

// Вставь импорт функции из твоего utils/media.js

import { resolveMediaUrl } from '@/utils/media'
const app = createApp(App)

app.use(createPinia())
app.use(router)

app.config.globalProperties.$api = api;
// ДОБАВЬ ВОТ ЭТУ СТРОКУ:
app.config.globalProperties.$media = resolveMediaUrl;

setUnauthorizedHandler(() => router.replace({ path: '/login', query: { reason: 'session-expired' } }))

app.mount('#app')
