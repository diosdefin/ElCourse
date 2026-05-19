<script setup>
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  email: '',
  role: 'student',
  password: '',
  confirmPassword: '',
})

const showPassword = ref(false)
const showConfirmPassword = ref(false)
const submitting = ref(false)
const formError = ref('')

const roleOptions = [
  {
    value: 'student',
    label: 'Студент',
    description: 'Прохождение курсов, тестов и развитие профиля навыков.',
  },
  {
    value: 'teacher',
    label: 'Преподаватель',
    description: 'Создание курсов, модулей, уроков и тестовой базы.',
  },
  {
    value: 'employer',
    label: 'Работодатель',
    description: 'Поиск кандидатов и отправка карьерных предложений.',
  },
]

const roleLabel = computed(() => roleOptions.find((item) => item.value === form.role)?.label || 'Студент')

const usernameIsValid = computed(() => {
  const value = form.username.trim()
  return value.length >= 3 && value.length <= 150 && /^[\w.@+-]+$/.test(value)
})

const emailIsValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()))
const passwordIsValid = computed(() => form.password.length >= 8 && form.password.length <= 128)
const passwordsMatch = computed(() => form.password && form.password === form.confirmPassword)

const passwordStrength = computed(() => {
  let score = 0
  if (form.password.length >= 8) score += 1
  if (/[A-ZА-Я]/.test(form.password)) score += 1
  if (/[a-zа-я]/.test(form.password)) score += 1
  if (/\d/.test(form.password)) score += 1
  if (/[^\w\s]/.test(form.password)) score += 1
  return score
})

const passwordStrengthLabel = computed(() => {
  if (!form.password) return 'Не указан'
  if (passwordStrength.value <= 2) return 'Слабый'
  if (passwordStrength.value <= 4) return 'Нормальный'
  return 'Сильный'
})

const passwordStrengthWidth = computed(() => `${Math.min(100, passwordStrength.value * 20)}%`)

const canSubmit = computed(() => (
  usernameIsValid.value
  && emailIsValid.value
  && passwordIsValid.value
  && passwordsMatch.value
  && !submitting.value
))

const redirectByRole = (role) => {
  if (role === 'teacher') return '/teacher'
  if (role === 'employer') return '/employer'
  return '/profile'
}

const fieldNames = {
  username: 'Логин',
  email: 'Email',
  password: 'Пароль',
  role: 'Роль',
  detail: 'Ошибка',
  non_field_errors: 'Ошибка',
}

const normalizeApiError = (error) => {
  const data = error?.response?.data
  if (!data) {
    return 'Не удалось создать аккаунт. Проверьте подключение к серверу.'
  }

  if (typeof data === 'string') {
    return data
  }

  if (data.detail) {
    return Array.isArray(data.detail) ? data.detail.join(' ') : data.detail
  }

  const messages = []
  Object.entries(data).forEach(([field, value]) => {
    const label = fieldNames[field] || field
    const text = Array.isArray(value) ? value.join(' ') : String(value)
    messages.push(`${label}: ${text}`)
  })

  return messages.join(' ') || 'Проверьте данные регистрации.'
}

const validateBeforeSubmit = () => {
  if (!usernameIsValid.value) {
    return 'Логин должен содержать 3–150 символов. Разрешены буквы, цифры и символы @ . + - _'
  }

  if (!emailIsValid.value) {
    return 'Введите корректный email.'
  }

  if (!passwordIsValid.value) {
    return 'Пароль должен содержать минимум 8 символов.'
  }

  if (!passwordsMatch.value) {
    return 'Подтверждение пароля не совпадает.'
  }

  return ''
}

const handleRegister = async () => {
  formError.value = ''
  const localError = validateBeforeSubmit()

  if (localError) {
    formError.value = localError
    return
  }

  submitting.value = true

  try {
    const payload = {
      username: form.username.trim(),
      email: form.email.trim(),
      password: form.password,
      role: form.role,
    }

    await api.post('/register/', payload)

    const tokenResponse = await api.post('/token/', {
      username: payload.username,
      password: payload.password,
    })

    const { access, refresh } = tokenResponse.data
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)

    const userResponse = await api.get('/users/me/', {
      withCredentials: true,
    })

    authStore.login(access, userResponse.data.role, userResponse.data)
    showSuccess(`Аккаунт создан. Роль: ${roleLabel.value}.`)
    router.push(redirectByRole(userResponse.data.role))
  } catch (error) {
    console.error('Ошибка регистрации:', error)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    const message = normalizeApiError(error)
    formError.value = message
    showError(message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex min-h-[calc(100svh-96px)] w-full items-top justify-center px-4 py-4 sm:px-6">
    <section class="w-full max-w-[720px]">
      <div class="card-glass rounded-[1.55rem] p-4 sm:p-5">
        <div class="flex flex-col items-center text-center">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-black text-white shadow-lg shadow-indigo-600/20">
            EL
          </div>

          <p class="mt-3 text-[10px] font-bold uppercase tracking-[0.24em] text-indigo-300/70">
            ElCourse
          </p>

          <h1 class="mt-2 text-xl font-black text-white sm:text-2xl">
            Создание аккаунта
          </h1>

         
        </div>

        <form class="mt-5 space-y-4" @submit.prevent="handleRegister">
          <div>
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="block text-xs font-bold text-slate-300">
                Роль в системе
              </label>

              <span class="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-2.5 py-1 text-[11px] font-bold text-indigo-200">
                {{ roleLabel }}
              </span>
            </div>

            <div class="grid gap-2 sm:grid-cols-3">
              <button
                v-for="option in roleOptions"
                :key="option.value"
                type="button"
                class="rounded-xl border px-3 py-2.5 text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                :class="form.role === option.value
                  ? 'border-indigo-400/70 bg-indigo-500/15 text-white shadow-lg shadow-indigo-950/20'
                  : 'border-slate-800 bg-slate-950/35 text-slate-300 hover:border-slate-600 hover:bg-slate-900'"
                @click="form.role = option.value"
              >
                <span class="block text-sm font-black">{{ option.label }}</span>
                <span class="mt-1 block line-clamp-2 text-[11px] leading-4 text-slate-400">
                  {{ option.description }}
                </span>
              </button>
            </div>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <div>
              <label for="register-username" class="mb-1.5 block text-xs font-bold text-slate-300">
                Логин
              </label>

              <input
                id="register-username"
                v-model.trim="form.username"
                type="text"
                required
                autocomplete="username"
                maxlength="150"
                class="input-control rounded-xl px-4 py-2.5 text-sm"
                placeholder="student_danik"
              >

              <p class="mt-1.5 text-[11px] leading-4 text-slate-500">
                3–150 символов: буквы, цифры, @ . + - _
              </p>
            </div>

            <div>
              <label for="register-email" class="mb-1.5 block text-xs font-bold text-slate-300">
                Email
              </label>

              <input
                id="register-email"
                v-model.trim="form.email"
                type="email"
                required
                autocomplete="email"
                maxlength="254"
                class="input-control rounded-xl px-4 py-2.5 text-sm"
                placeholder="name@example.com"
              >

              <p class="mt-1.5 text-[11px] leading-4 text-slate-500">
                Используется для профиля и связи.
              </p>
            </div>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <div>
              <div class="mb-1.5 flex items-center justify-between gap-3">
                <label for="register-password" class="block text-xs font-bold text-slate-300">
                  Пароль
                </label>

                <span class="text-[11px] font-semibold text-slate-500">
                  {{ passwordStrengthLabel }}
                </span>
              </div>

              <div class="relative">
                <input
                  id="register-password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  autocomplete="new-password"
                  maxlength="128"
                  class="input-control rounded-xl py-2.5 pl-4 pr-12 text-sm"
                  placeholder="Минимум 8 символов"
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

              <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all"
                  :style="{ width: passwordStrengthWidth }"
                ></div>
              </div>
            </div>

            <div>
              <label for="register-confirm-password" class="mb-1.5 block text-xs font-bold text-slate-300">
                Повторите пароль
              </label>

              <div class="relative">
                <input
                  id="register-confirm-password"
                  v-model="form.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  required
                  autocomplete="new-password"
                  maxlength="128"
                  class="input-control rounded-xl py-2.5 pl-4 pr-12 text-sm"
                  placeholder="Повторите пароль"
                >

                <button
                  type="button"
                  class="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                  :aria-label="showConfirmPassword ? 'Скрыть пароль' : 'Показать пароль'"
                  :title="showConfirmPassword ? 'Скрыть пароль' : 'Показать пароль'"
                  @click="showConfirmPassword = !showConfirmPassword"
                >
                  <svg v-if="!showConfirmPassword" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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

              <p
                v-if="form.confirmPassword"
                class="mt-1.5 text-[11px] leading-4"
                :class="passwordsMatch ? 'text-emerald-300' : 'text-rose-300'"
              >
                {{ passwordsMatch ? 'Пароли совпадают.' : 'Пароли не совпадают.' }}
              </p>
            </div>
          </div>

          <div v-if="formError" class="rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs leading-5 text-rose-100">
            {{ formError }}
          </div>

          <button
            type="submit"
            :disabled="!canSubmit"
            class="btn-primary min-h-[42px] w-full rounded-xl py-2.5 text-sm font-black"
          >
            {{ submitting ? 'Создание аккаунта...' : 'Создать аккаунт' }}
          </button>
        </form>

        <div class="mt-4 rounded-xl border border-slate-800 bg-slate-950/35 px-3 py-3 text-center text-xs text-slate-400">
          Уже есть аккаунт?
          <RouterLink to="/login" class="font-bold text-indigo-300 transition hover:text-indigo-200">
            Войти в систему
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>