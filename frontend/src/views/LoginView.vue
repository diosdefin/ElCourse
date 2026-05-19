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
  <div class="mx-auto flex min-h-[calc(100svh-96px)] w-full items-top justify-center px-4 py-4 sm:px-6">
    <section class="w-full max-w-[380px]">
      <div class="card-glass rounded-[1.55rem] p-4 sm:p-5">
        <div class="text-center">
          <div class="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-black text-white shadow-lg shadow-indigo-600/20">
            EL
          </div>

          <p class="mt-3 text-[10px] font-bold uppercase tracking-[0.24em] text-indigo-300/70">
            ElCourse
          </p>

          <h1 class="mt-2 text-xl font-black text-white sm:text-2xl">
            Вход в аккаунт
          </h1>

          <p class="mx-auto mt-1.5 max-w-xs text-xs leading-5 text-slate-400">
            Введите логин и пароль, чтобы продолжить работу с платформой.
          </p>
        </div>

        <form class="mt-5 space-y-3.5" @submit.prevent="handleLogin">
          <div>
            <label for="login-username" class="mb-1.5 block text-xs font-bold text-slate-300">
              Логин
            </label>

            <input
              id="login-username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              maxlength="150"
              class="input-control rounded-xl px-4 py-2.5 text-sm"
              placeholder="Введите логин"
            >
          </div>

          <div>
            <label for="login-password" class="mb-1.5 block text-xs font-bold text-slate-300">
              Пароль
            </label>

            <div class="relative">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                maxlength="128"
                class="input-control rounded-xl py-2.5 pl-4 pr-12 text-sm"
                placeholder="Введите пароль"
              >

              <button
                type="button"
                class="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                :title="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M2.75 12s3.25-6.25 9.25-6.25S21.25 12 21.25 12 18 18.25 12 18.25 2.75 12 2.75 12Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M12 15.1a3.1 3.1 0 1 0 0-6.2 3.1 3.1 0 0 0 0 6.2Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>

                <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3.25 3.25l17.5 17.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
                  <path d="M10.7 5.9c.42-.1.86-.15 1.3-.15 6 0 9.25 6.25 9.25 6.25a17.78 17.78 0 0 1-2.63 3.49" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M6.46 7.45C4.08 9.06 2.75 12 2.75 12S6 18.25 12 18.25c1.66 0 3.1-.48 4.31-1.18" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M9.88 9.88a3.1 3.1 0 0 0 4.24 4.24" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </div>

          <div v-if="formError" class="rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
            {{ formError }}
          </div>

          <button
            type="submit"
            :disabled="!canSubmit"
            class="btn-primary min-h-[42px] w-full rounded-xl py-2.5 text-sm font-black"
          >
            {{ submitting ? 'Вход...' : 'Войти в аккаунт' }}
          </button>
        </form>

        <div class="mt-4 rounded-xl border border-slate-800 bg-slate-950/35 px-3 py-3 text-center text-xs text-slate-400">
          Нет аккаунта?
          <RouterLink to="/register" class="font-bold text-indigo-300 transition hover:text-indigo-200">
            Создать аккаунт
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>
