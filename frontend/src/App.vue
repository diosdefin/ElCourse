<script setup>
import { ref, onMounted, watch } from 'vue' // ДОБАВЛЕН watch
import { RouterView, RouterLink } from 'vue-router'
import { useAuthStore } from './stores/auth'
import axios from 'axios'

const authStore = useAuthStore()
const unreadCount = ref(0)

const checkNotifications = async () => {
  if (!authStore.isAuthenticated) return
  try {
    const token = localStorage.getItem('access_token')
    const res = await axios.get('http://127.0.0.1:8000/api/notifications/count/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    unreadCount.value = res.data.unread_count
  } catch (error) {
    console.error('Ошибка загрузки уведомлений:', error)
  }
}

// Следим за авторизацией: как только вошли - сразу проверяем колокольчик!
watch(() => authStore.isAuthenticated, (isAuth) => {
  if (isAuth) {
    checkNotifications()
  }
})

onMounted(() => {
  authStore.initialize()
  checkNotifications() 
  // Слушаем сигнал обновления от других страниц
  window.addEventListener('update-bell', checkNotifications)
  // setInterval(checkNotifications, 10000)
})
</script>

<template>
  <div class="min-h-screen bg-slate-900 text-slate-300 font-sans selection:bg-indigo-500/30">
    
    <header class="sticky top-0 z-50 backdrop-blur-lg bg-slate-900/80 border-b border-slate-800 shadow-lg">
      <div class="container mx-auto flex justify-between items-center px-6 py-4">
        <RouterLink to="/" class="text-2xl font-black tracking-widest text-white flex items-center gap-2">
          <div class="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center text-sm shadow-lg shadow-indigo-500/20">EL</div>
          COURSE
        </RouterLink>
        
        <nav class="flex items-center gap-8">
          <RouterLink to="/" class="text-slate-400 hover:text-white font-medium transition-colors">Курсы</RouterLink>
          
          <RouterLink v-if="!authStore.isAuthenticated" to="/login" 
            class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-medium transition-all shadow-lg shadow-indigo-500/25">
            Вход / Регистрация
          </RouterLink>

          <div v-else class="flex items-center gap-6 bg-slate-800/50 px-2 py-1.5 rounded-full border border-slate-700/50">
            <div class="flex items-center gap-2 pl-3">
              <span class="relative flex h-3 w-3">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span class="text-emerald-400 text-sm font-semibold hidden sm:block">В сети</span>
            </div>
            
      <RouterLink 
  v-if="authStore.isTeacher" 
  to="/teacher" 
  class="text-slate-200 hover:text-indigo-400 font-medium transition-colors text-sm"
>
  Кабинет автора
</RouterLink>
<RouterLink to="/notifications" class="relative p-2 text-slate-400 hover:text-indigo-400 transition-colors">
  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>
  
  <span v-if="unreadCount > 0" class="absolute -top-1 -right-1 bg-rose-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center shadow-lg">
    {{ unreadCount > 99 ? '99+' : unreadCount }}
  </span>
</RouterLink>

<RouterLink v-if="authStore.isEmployer" to="/employer" 
    class="text-emerald-400 hover:text-emerald-300 font-bold transition-colors text-sm border-l border-slate-700 pl-4">
    Поиск талантов
  </RouterLink>

            <RouterLink to="/profile" class="text-slate-200 hover:text-indigo-400 font-medium transition-colors text-sm">
              Мой профиль
            </RouterLink>
            
            <button @click="authStore.logout" 
              class="px-4 py-1.5 bg-slate-700/50 text-slate-300 rounded-full hover:bg-rose-500/80 hover:text-white transition-colors text-sm font-medium">
              Выйти
            </button>
          </div>
        </nav>
      </div>
    </header>

    <main class="container mx-auto px-4 py-8">
      <RouterView />
    </main>
  </div>
</template>