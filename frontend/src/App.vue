<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import api from './api'
import ToastHost from './components/ToastHost.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const unreadCount = ref(0)

const checkNotifications = async () => {
  if (!authStore.isAuthenticated) {
    unreadCount.value = 0
    return
  }

  try {
    const response = await api.get('/notifications/count/')
    unreadCount.value = response.data.unread_count
  } catch (error) {
    console.error('Ошибка загрузки уведомлений:', error)
  }
}

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      checkNotifications()
    } else {
      unreadCount.value = 0
    }
  }
)

onMounted(() => {
  authStore.initialize()
  checkNotifications()
  window.addEventListener('update-bell', checkNotifications)
})
</script>

<template>
  <div class="min-h-screen bg-slate-900 text-slate-300 selection:bg-indigo-500/30">
    <ToastHost />

    <header class="sticky top-0 z-50 border-b border-slate-800 bg-slate-900/80 shadow-lg backdrop-blur-lg">
      <div class="container mx-auto flex flex-wrap items-center justify-between gap-4 px-6 py-4">
        <RouterLink to="/" class="flex items-center gap-2 text-2xl font-black tracking-widest text-white">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-sm shadow-lg shadow-indigo-500/20">EL</div>
          COURSE
        </RouterLink>

        <nav class="flex flex-wrap items-center gap-3 sm:gap-4">
          <RouterLink to="/" class="rounded-full px-3 py-2 text-sm font-medium text-slate-400 transition hover:text-white">
            Главная
          </RouterLink>
          <RouterLink to="/community" class="rounded-full px-3 py-2 text-sm font-medium text-slate-400 transition hover:text-white">
            {{ authStore.isEmployer ? 'Таланты' : 'Комьюнити' }}
          </RouterLink>

          <RouterLink
            v-if="!authStore.isAuthenticated"
            to="/login"
            class="rounded-full bg-indigo-600 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-500"
          >
            Вход / Регистрация
          </RouterLink>

          <div
            v-else
            class="flex flex-wrap items-center gap-3 rounded-full border border-slate-700/50 bg-slate-800/50 px-3 py-2"
          >
            <div class="hidden items-center gap-2 pl-2 sm:flex">
              <span class="relative flex h-3 w-3">
                <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
              </span>
              <span class="text-sm font-semibold text-emerald-400">В сети</span>
            </div>

            <RouterLink
              v-if="authStore.isTeacher"
              to="/teacher"
              class="px-3 py-1 text-sm font-medium text-slate-200 transition hover:text-indigo-400"
            >
              Кабинет автора
            </RouterLink>

            <RouterLink
              to="/notifications"
              class="relative rounded-full p-2 text-slate-400 transition hover:text-indigo-400"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>

              <span
                v-if="unreadCount > 0"
                class="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-xs text-white shadow-lg"
              >
                {{ unreadCount > 99 ? '99+' : unreadCount }}
              </span>
            </RouterLink>

            <RouterLink
              to="/profile"
              class="px-3 py-1 text-sm font-medium text-slate-200 transition hover:text-indigo-400"
            >
              Мой профиль
            </RouterLink>
          <RouterLink
  to="/settings"
  class="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition-all duration-200 hover:bg-slate-700/50 hover:text-indigo-400"
>
  <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
</RouterLink>

            <RouterLink
              to="/profile"
              class="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-slate-600 bg-slate-900"
            >
              <img
                v-if="authStore.displayAvatar"
                :src="authStore.displayAvatar"
                alt="avatar"
                class="h-full w-full object-cover"
              >
              <span v-else class="text-sm font-bold text-slate-300">{{ authStore.displayInitial }}</span>
            </RouterLink>


            <button
              class="rounded-full bg-slate-700/60 px-4 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-rose-500/80 hover:text-white"
              @click="authStore.logout"
            >
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
