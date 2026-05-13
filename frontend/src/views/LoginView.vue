<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showInfo, showSuccess } from '../utils/toast'

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const formError = ref('')

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const canSubmit = computed(() => username.value.trim().length >= 2 && password.value.length >= 4 && !submitting.value)

const redirectByRole = (role) => {
  if (role === 'teacher') return '/teacher'
  if (role === 'employer') return '/employer'
  return '/profile'
}

const handleLogin = async () => {
  formError.value = ''

  if (!username.value.trim()) {
    formError.value = 'Введите логин.'
    return
  }

  if (!password.value) {
    formError.value = 'Введите пароль.'
    return
  }

  submitting.value = true

  try {
    const tokenResponse = await api.post('/token/', {
      username: username.value.trim(),
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
    router.push(redirectByRole(userRole))
  } catch (error) {
    console.error('Ошибка входа:', error)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    formError.value = 'Неверный логин или пароль.'
    showError('Неверный логин или пароль.')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  if (route.query.reason === 'session-expired') {
    showInfo('Сессия истекла. Пожалуйста, войдите снова.')
  }
})
</script>

<template>
  <div class="mx-auto flex min-h-[calc(100vh-140px)] w-full max-w-6xl items-center justify-center py-6 sm:px-4 sm:py-10">
    <section class="w-full max-w-md">
      <div class="rounded-[2rem] border border-slate-800 bg-slate-900/72 p-5 shadow-2xl shadow-slate-950/30 backdrop-blur sm:p-9">
        <div class="text-center">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-base font-black text-white shadow-lg shadow-indigo-600/20 sm:h-14 sm:w-14 sm:text-lg">
            EL
          </div>
          <p class="mt-6 text-xs font-bold uppercase tracking-[0.28em] text-indigo-300/70">ElCourse</p>
          <h1 class="mt-3 text-2xl font-black text-white sm:text-3xl">Вход в аккаунт</h1>
          <p class="mt-2 text-sm leading-6 text-slate-400">
            Введите логин и пароль, чтобы продолжить обучение или работу с курсами.
          </p>
        </div>

        <form class="mt-8 space-y-5" @submit.prevent="handleLogin">
          <div>
            <label for="login-username" class="mb-2 block text-sm font-bold text-slate-300">Логин</label>
            <input
              id="login-username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              maxlength="150"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-5 py-3.5 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-500/10"
              placeholder="Введите логин"
            >
          </div>

          <div>
            <label for="login-password" class="mb-2 block text-sm font-bold text-slate-300">Пароль</label>
            <div class="relative">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                maxlength="128"
                class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 py-3.5 pl-5 pr-14 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-500/10"
                placeholder="Введите пароль"
              >
              <button
                type="button"
                class="absolute right-3 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-slate-400 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                :title="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M2.75 12s3.25-6.25 9.25-6.25S21.25 12 21.25 12 18 18.25 12 18.25 2.75 12 2.75 12Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M12 15.1a3.1 3.1 0 1 0 0-6.2 3.1 3.1 0 0 0 0 6.2Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3.25 3.25l17.5 17.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                  <path d="M10.7 5.9c.42-.1.86-.15 1.3-.15 6 0 9.25 6.25 9.25 6.25a17.78 17.78 0 0 1-2.63 3.49" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M6.46 7.45C4.08 9.06 2.75 12 2.75 12S6 18.25 12 18.25c1.66 0 3.1-.48 4.31-1.18" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M9.88 9.88a3.1 3.1 0 0 0 4.24 4.24" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </div>

          <div v-if="formError" class="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {{ formError }}
          </div>

          <button
            type="submit"
            :disabled="!canSubmit"
            class="w-full rounded-2xl bg-indigo-600 px-5 py-4 text-base font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ submitting ? 'Вход...' : 'Войти в аккаунт' }}
          </button>
        </form>

        <div class="mt-7 rounded-2xl border border-slate-800 bg-slate-950/35 p-4 text-center text-sm text-slate-400">
          Нет аккаунта?
          <RouterLink to="/register" class="font-bold text-indigo-300 transition hover:text-indigo-200">
            Создать аккаунт
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
