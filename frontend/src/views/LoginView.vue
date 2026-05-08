<template>
  <div class="mx-auto mt-20 max-w-md px-4">
    <div class="rounded-3xl border border-slate-700/50 bg-slate-800/40 p-10 shadow-2xl backdrop-blur-xl">
      <div class="mb-10 text-center">
        <div class="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500 text-xl font-black text-white shadow-lg shadow-indigo-500/20">
          EL
        </div>
        <h2 class="mb-2 text-3xl font-black text-slate-100">Авторизация</h2>
        <p class="text-slate-400">Введите свои данные для входа</p>
      </div>

      <form class="space-y-6" @submit.prevent="handleLogin">
        <div>
          <label class="mb-2 ml-1 block text-sm font-bold text-slate-400">Логин</label>
          <input
            v-model="username"
            type="text"
            required
            class="w-full rounded-2xl border border-slate-700 bg-slate-900/50 px-5 py-3 text-slate-100 outline-none transition-all placeholder:text-slate-600 focus:border-transparent focus:ring-2 focus:ring-indigo-500"
            placeholder="Ваш логин"
          >
        </div>

        <div>
          <label class="mb-2 ml-1 block text-sm font-bold text-slate-400">Пароль</label>
          <input
            v-model="password"
            type="password"
            required
            class="w-full rounded-2xl border border-slate-700 bg-slate-900/50 px-5 py-3 text-slate-100 outline-none transition-all placeholder:text-slate-600 focus:border-transparent focus:ring-2 focus:ring-indigo-500"
            placeholder="••••••••"
          >
        </div>

        <button
          type="submit"
          class="w-full rounded-2xl bg-indigo-600 py-4 text-lg font-bold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500 active:scale-95"
        >
          Войти в аккаунт
        </button>
      </form>

      <div class="mt-8 text-center text-sm text-slate-500">
        Впервые у нас?
        <RouterLink to="/register" class="font-bold text-indigo-400 transition-colors hover:text-indigo-300">
          Создайте аккаунт
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showInfo, showSuccess } from '../utils/toast'

const username = ref('')
const password = ref('')
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const handleLogin = async () => {
  try {
    const tokenResponse = await api.post('/token/', {
      username: username.value,
      password: password.value,
    })

    const { access, refresh } = tokenResponse.data

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)

    const userResponse = await api.get('/users/me/', {
      withCredentials: true,
    })
    const userRole = userResponse.data.role

    authStore.login(access, userRole, userResponse.data)
    showSuccess('Вы успешно вошли в аккаунт.')

    if (userRole === 'teacher') {
      router.push('/teacher')
    } else {
      router.push('/profile')
    }
  } catch (error) {
    console.error('Ошибка входа:', error)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    showError('Неверный логин или пароль.')
  }
}

onMounted(() => {
  if (route.query.reason === 'session-expired') {
    showInfo('Сессия истекла. Пожалуйста, войдите снова.')
  }
})
</script>
