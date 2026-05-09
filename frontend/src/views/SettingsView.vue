<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import {
  changePassword,
  getUserSettings,
  updateUserSettings as patchUserSettings,
} from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const authStore = useAuthStore()

const tabs = [
  { key: 'basic', label: 'Профиль', hint: 'Аватар и описание' },
  { key: 'contacts', label: 'Контакты', hint: 'Публичные ссылки' },
  { key: 'security', label: 'Безопасность', hint: 'Смена пароля' },
]

const limits = {
  bio: 1200,
  location: 120,
  telegram: 80,
  github: 160,
  linkedin: 220,
}

const activeTab = ref('basic')
const loading = ref(true)
const saving = ref(false)
const changingPassword = ref(false)
const avatarPreview = ref(null)
const avatarInputKey = ref(0)
const originalData = ref(null)

const form = reactive({
  username: '',
  email: '',
  avatar: null,
  bio: '',
  location: '',
  telegram: '',
  github: '',
  linkedin: '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const sanitizeText = (value) => {
  if (!value) return ''
  return `${value}`.replace(/[<>]/g, '').trim()
}

const isDangerous = (value) => /<script|javascript:|onerror=|onload=|data:text\/html/i.test(value || '')

const roleLabel = computed(() => {
  if (authStore.isTeacher) return 'Преподаватель'
  if (authStore.isEmployer) return 'Работодатель'
  if (authStore.isStudent) return 'Студент'
  return 'Пользователь'
})

const initials = computed(() => form.username?.[0]?.toUpperCase() || 'U')

const bioCount = computed(() => sanitizeText(form.bio).length)
const locationCount = computed(() => sanitizeText(form.location).length)
const telegramCount = computed(() => sanitizeText(form.telegram).length)
const githubCount = computed(() => sanitizeText(form.github).length)
const linkedinCount = computed(() => sanitizeText(form.linkedin).length)

const contactCompletion = computed(() => {
  const filled = ['location', 'telegram', 'github', 'linkedin'].filter((field) => sanitizeText(form[field])).length
  return Math.round((filled / 4) * 100)
})

const applySettings = (data) => {
  originalData.value = {
    avatar: data.avatar || '',
    bio: data.bio || '',
    location: data.location || '',
    telegram: data.telegram || '',
    github: data.github || '',
    linkedin: data.linkedin || '',
  }

  form.username = data.username || ''
  form.email = data.email || ''
  form.avatar = null
  form.bio = data.bio || ''
  form.location = data.location || ''
  form.telegram = data.telegram || ''
  form.github = data.github || ''
  form.linkedin = data.linkedin || ''
  avatarPreview.value = data.avatar || null
  avatarInputKey.value += 1
}

const hasProfileChanges = computed(() => {
  if (!originalData.value) return false
  if (form.avatar) return true

  return (
    sanitizeText(form.bio) !== originalData.value.bio ||
    sanitizeText(form.location) !== originalData.value.location ||
    sanitizeText(form.telegram) !== originalData.value.telegram ||
    sanitizeText(form.github) !== originalData.value.github ||
    sanitizeText(form.linkedin) !== originalData.value.linkedin
  )
})

const passwordStrength = computed(() => {
  const password = passwordForm.new_password || ''
  let score = 0
  if (password.length >= 8) score += 1
  if (/[A-ZА-Я]/.test(password)) score += 1
  if (/[0-9]/.test(password)) score += 1
  if (/[^A-Za-zА-Яа-я0-9]/.test(password)) score += 1

  if (!password) return { label: 'Не указан', width: '0%', tone: 'bg-slate-700' }
  if (score <= 1) return { label: 'Слабый', width: '25%', tone: 'bg-rose-500' }
  if (score === 2) return { label: 'Средний', width: '50%', tone: 'bg-amber-400' }
  if (score === 3) return { label: 'Хороший', width: '75%', tone: 'bg-cyan-400' }
  return { label: 'Надёжный', width: '100%', tone: 'bg-emerald-400' }
})

const fetchSettings = async () => {
  loading.value = true
  try {
    const response = await getUserSettings()
    applySettings(response.data)
    authStore.updateUserSettings(response.data)
  } catch (error) {
    console.error('Ошибка загрузки настроек:', error)
    showError('Не удалось загрузить настройки профиля.')
  } finally {
    loading.value = false
  }
}

const onAvatarChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
  if (!allowedTypes.includes(file.type)) {
    showError('Можно загрузить только JPEG, PNG или WEBP изображение.')
    event.target.value = ''
    return
  }

  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    showError('Размер аватара не должен превышать 2 МБ.')
    event.target.value = ''
    return
  }

  if (avatarPreview.value && avatarPreview.value.startsWith('blob:')) {
    URL.revokeObjectURL(avatarPreview.value)
  }

  form.avatar = file
  avatarPreview.value = URL.createObjectURL(file)
}

const resetAvatar = () => {
  form.avatar = null
  avatarPreview.value = originalData.value?.avatar || null
  avatarInputKey.value += 1
}

const validateProfile = () => {
  const checks = [
    { field: 'bio', label: 'Описание', max: limits.bio },
    { field: 'location', label: 'Локация', max: limits.location },
    { field: 'telegram', label: 'Telegram', max: limits.telegram },
    { field: 'github', label: 'GitHub', max: limits.github },
    { field: 'linkedin', label: 'LinkedIn', max: limits.linkedin },
  ]

  for (const check of checks) {
    const value = sanitizeText(form[check.field])
    if (value.length > check.max) {
      showError(`${check.label}: максимум ${check.max} символов.`)
      return false
    }
    if (isDangerous(value)) {
      showError(`${check.label}: поле содержит недопустимый код или ссылку.`)
      return false
    }
  }

  const telegram = sanitizeText(form.telegram)
  if (telegram && !/^@?[a-zA-Z0-9_]{5,32}$/.test(telegram) && !/^https?:\/\/(t\.me|telegram\.me)\//i.test(telegram)) {
    showError('Telegram укажите как @username или ссылку t.me.')
    return false
  }

  const github = sanitizeText(form.github)
  if (github && !/^[a-zA-Z0-9-]{1,39}$/.test(github) && !/^https?:\/\/(www\.)?github\.com\//i.test(github)) {
    showError('GitHub укажите как username или ссылку github.com.')
    return false
  }

  const linkedin = sanitizeText(form.linkedin)
  if (linkedin && /^https?:\/\//i.test(linkedin) && !/^https?:\/\/(www\.)?linkedin\.com\//i.test(linkedin)) {
    showError('LinkedIn должен быть ссылкой на linkedin.com или коротким именем профиля.')
    return false
  }

  return true
}

const buildPatchPayload = () => {
  const payload = {}

  const cleanBio = sanitizeText(form.bio)
  const cleanLocation = sanitizeText(form.location)
  const cleanTelegram = sanitizeText(form.telegram)
  const cleanGithub = sanitizeText(form.github)
  const cleanLinkedin = sanitizeText(form.linkedin)

  if (cleanBio !== originalData.value.bio) payload.bio = cleanBio
  if (cleanLocation !== originalData.value.location) payload.location = cleanLocation
  if (cleanTelegram !== originalData.value.telegram) payload.telegram = cleanTelegram
  if (cleanGithub !== originalData.value.github) payload.github = cleanGithub
  if (cleanLinkedin !== originalData.value.linkedin) payload.linkedin = cleanLinkedin
  if (form.avatar) payload.avatar = form.avatar

  return payload
}

const saveProfile = async () => {
  if (!originalData.value || saving.value) return
  if (!validateProfile()) return

  const patchPayload = buildPatchPayload()
  if (!Object.keys(patchPayload).length) {
    showSuccess('Изменений нет.')
    return
  }

  saving.value = true
  try {
    const needsMultipart = Boolean(patchPayload.avatar)
    let response

    if (needsMultipart) {
      const formData = new FormData()
      for (const [key, value] of Object.entries(patchPayload)) {
        formData.append(key, value)
      }
      response = await patchUserSettings(formData, true)
    } else {
      response = await patchUserSettings(patchPayload, false)
    }

    applySettings(response.data)
    authStore.updateUserSettings(response.data)
    showSuccess('Настройки сохранены.')
  } catch (error) {
    console.error('Ошибка сохранения профиля:', error)
    const detail = error.response?.data
    const firstError = detail && Object.values(detail).flat().find(Boolean)
    showError(firstError || detail?.detail || 'Не удалось сохранить изменения. Попробуйте ещё раз.')
  } finally {
    saving.value = false
  }
}

const changeUserPassword = async () => {
  if (!passwordForm.old_password || !passwordForm.new_password || !passwordForm.confirm_password) {
    showError('Пожалуйста, заполните все поля пароля.')
    return
  }

  if (passwordForm.new_password.length < 8) {
    showError('Новый пароль должен содержать минимум 8 символов.')
    return
  }

  if (passwordForm.new_password !== passwordForm.confirm_password) {
    showError('Подтверждение нового пароля не совпадает.')
    return
  }

  if (passwordForm.old_password === passwordForm.new_password) {
    showError('Новый пароль должен отличаться от текущего.')
    return
  }

  changingPassword.value = true
  try {
    const response = await changePassword({ ...passwordForm })
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    showSuccess(response.data?.detail || 'Пароль успешно изменён.')
  } catch (error) {
    console.error('Ошибка смены пароля:', error)
    const data = error.response?.data || {}
    const firstError = Object.values(data).flat().find(Boolean)
    showError(firstError || 'Не удалось изменить пароль.')
  } finally {
    changingPassword.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="mx-auto mt-8 max-w-6xl space-y-6 px-4 pb-12">
    <section class="rounded-[28px] border border-slate-700/60 bg-slate-900/55 p-6 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300">Аккаунт</p>
          <h1 class="mt-2 text-3xl font-black text-slate-100">Настройки</h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-400">
            Обновите публичные данные, контакты и параметры безопасности. Эти данные используются в профиле и карьерном контуре.
          </p>
        </div>

        <div class="flex items-center gap-4 rounded-2xl border border-slate-700/70 bg-slate-950/35 p-3">
          <div class="h-14 w-14 overflow-hidden rounded-2xl border border-slate-700 bg-slate-950">
            <img v-if="avatarPreview" :src="avatarPreview" alt="Аватар" class="h-full w-full object-cover">
            <div v-else class="flex h-full w-full items-center justify-center text-lg font-black text-slate-400">
              {{ initials }}
            </div>
          </div>
          <div class="min-w-0">
            <p class="truncate text-sm font-bold text-slate-100">{{ form.username || 'Пользователь' }}</p>
            <p class="text-xs text-slate-500">{{ roleLabel }}</p>
            <p class="mt-1 truncate text-xs text-slate-400">{{ form.email || 'email не указан' }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-[28px] border border-slate-700/60 bg-slate-900/55 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="grid border-b border-slate-700/60 p-2 sm:grid-cols-3">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="rounded-2xl px-4 py-3 text-left transition"
          :class="activeTab === tab.key
            ? 'bg-indigo-500/15 text-slate-100 ring-1 ring-indigo-400/40'
            : 'text-slate-400 hover:bg-slate-950/35 hover:text-slate-200'"
          @click="activeTab = tab.key"
        >
          <span class="block text-sm font-bold">{{ tab.label }}</span>
          <span class="mt-1 block text-xs text-slate-500">{{ tab.hint }}</span>
        </button>
      </div>

      <div v-if="loading" class="flex h-64 flex-col items-center justify-center gap-3 text-slate-400">
        <div class="h-9 w-9 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent"></div>
        <p class="text-sm">Загружаем настройки...</p>
      </div>

      <div v-else class="p-5 sm:p-6">
        <template v-if="activeTab === 'basic'">
          <div class="grid gap-6 lg:grid-cols-[260px,1fr]">
            <aside class="rounded-3xl border border-slate-700/70 bg-slate-950/35 p-5">
              <div class="mx-auto h-36 w-36 overflow-hidden rounded-3xl border border-slate-700 bg-slate-950 shadow-lg shadow-slate-950/30">
                <img v-if="avatarPreview" :src="avatarPreview" alt="Аватар" class="h-full w-full object-cover">
                <div v-else class="flex h-full w-full items-center justify-center text-4xl font-black text-slate-600">
                  {{ initials }}
                </div>
              </div>

              <div class="mt-5 space-y-2">
                <label class="flex cursor-pointer items-center justify-center rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-500">
                  Выбрать аватар
                  <input
                    :key="avatarInputKey"
                    type="file"
                    class="hidden"
                    accept="image/jpeg,image/png,image/webp"
                    @change="onAvatarChange"
                  >
                </label>
                <button
                  v-if="form.avatar"
                  type="button"
                  class="w-full rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
                  @click="resetAvatar"
                >
                  Отменить выбор
                </button>
              </div>

              <p class="mt-4 text-xs leading-5 text-slate-500">
                Поддерживаются JPEG, PNG и WEBP. Максимальный размер — 2 МБ.
              </p>
            </aside>

            <div class="space-y-5">
              <div class="grid gap-4 sm:grid-cols-2">
                <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 px-4 py-3">
                  <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Логин</p>
                  <p class="mt-1 truncate text-sm font-semibold text-slate-200">{{ form.username || 'Не указан' }}</p>
                </div>
                <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 px-4 py-3">
                  <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Email</p>
                  <p class="mt-1 truncate text-sm font-semibold text-slate-200">{{ form.email || 'Не указан' }}</p>
                </div>
              </div>

              <div>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="text-sm font-semibold text-slate-300">О себе</label>
                  <span class="text-xs" :class="bioCount > limits.bio ? 'text-rose-400' : 'text-slate-500'">
                    {{ bioCount }}/{{ limits.bio }}
                  </span>
                </div>
                <textarea
                  v-model="form.bio"
                  rows="5"
                  :maxlength="limits.bio + 50"
                  class="w-full resize-y rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm leading-6 text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                  placeholder="Кратко расскажите о себе, опыте, направлении обучения или преподавания."
                ></textarea>
              </div>

              <div>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="text-sm font-semibold text-slate-300">Локация</label>
                  <span class="text-xs" :class="locationCount > limits.location ? 'text-rose-400' : 'text-slate-500'">
                    {{ locationCount }}/{{ limits.location }}
                  </span>
                </div>
                <input
                  v-model="form.location"
                  type="text"
                  :maxlength="limits.location + 20"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                  placeholder="Например: Бишкек, Кыргызстан"
                >
              </div>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'contacts'">
          <div class="grid gap-6 lg:grid-cols-[1fr,280px]">
            <div class="grid gap-4">
              <div>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="text-sm font-semibold text-slate-300">Telegram</label>
                  <span class="text-xs" :class="telegramCount > limits.telegram ? 'text-rose-400' : 'text-slate-500'">
                    {{ telegramCount }}/{{ limits.telegram }}
                  </span>
                </div>
                <input
                  v-model="form.telegram"
                  type="text"
                  :maxlength="limits.telegram + 20"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                  placeholder="@username или https://t.me/username"
                >
              </div>

              <div>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="text-sm font-semibold text-slate-300">GitHub</label>
                  <span class="text-xs" :class="githubCount > limits.github ? 'text-rose-400' : 'text-slate-500'">
                    {{ githubCount }}/{{ limits.github }}
                  </span>
                </div>
                <input
                  v-model="form.github"
                  type="text"
                  :maxlength="limits.github + 20"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                  placeholder="username или https://github.com/username"
                >
              </div>

              <div>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="text-sm font-semibold text-slate-300">LinkedIn</label>
                  <span class="text-xs" :class="linkedinCount > limits.linkedin ? 'text-rose-400' : 'text-slate-500'">
                    {{ linkedinCount }}/{{ limits.linkedin }}
                  </span>
                </div>
                <input
                  v-model="form.linkedin"
                  type="text"
                  :maxlength="limits.linkedin + 20"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                  placeholder="username или ссылка на профиль LinkedIn"
                >
              </div>
            </div>

            <aside class="rounded-3xl border border-slate-700/70 bg-slate-950/35 p-5">
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-emerald-300">Заполненность</p>
              <div class="mt-4 flex items-end justify-between">
                <span class="text-4xl font-black text-white">{{ contactCompletion }}%</span>
                <span class="text-xs text-slate-500">публичные данные</span>
              </div>
              <div class="mt-4 h-2 rounded-full bg-slate-800">
                <div class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400" :style="{ width: `${contactCompletion}%` }"></div>
              </div>
              <p class="mt-4 text-xs leading-5 text-slate-500">
                Контакты помогают работодателям и участникам платформы быстрее понять, как с вами связаться.
              </p>
            </aside>
          </div>
        </template>

        <template v-if="activeTab === 'security'">
          <div class="grid gap-6 lg:grid-cols-[1fr,280px]">
            <div class="max-w-2xl space-y-4">
              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-300">Текущий пароль</label>
                <input
                  v-model="passwordForm.old_password"
                  type="password"
                  autocomplete="current-password"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                >
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-300">Новый пароль</label>
                <input
                  v-model="passwordForm.new_password"
                  type="password"
                  autocomplete="new-password"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                >
                <div class="mt-3 flex items-center gap-3">
                  <div class="h-2 flex-1 rounded-full bg-slate-800">
                    <div class="h-full rounded-full transition-all" :class="passwordStrength.tone" :style="{ width: passwordStrength.width }"></div>
                  </div>
                  <span class="w-20 text-right text-xs font-semibold text-slate-400">{{ passwordStrength.label }}</span>
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-300">Повторите новый пароль</label>
                <input
                  v-model="passwordForm.confirm_password"
                  type="password"
                  autocomplete="new-password"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/45 px-4 py-3 text-sm text-slate-200 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/15"
                >
              </div>

              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="changingPassword"
                @click="changeUserPassword"
              >
                <span v-if="changingPassword" class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
                {{ changingPassword ? 'Смена пароля...' : 'Сменить пароль' }}
              </button>
            </div>

            <aside class="rounded-3xl border border-slate-700/70 bg-slate-950/35 p-5">
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-cyan-300">Рекомендации</p>
              <ul class="mt-4 space-y-3 text-xs leading-5 text-slate-500">
                <li>Используйте минимум 8 символов.</li>
                <li>Добавьте цифры, заглавные буквы и специальные символы.</li>
                <li>Не используйте пароль от других сервисов.</li>
              </ul>
            </aside>
          </div>
        </template>
      </div>

      <div v-if="!loading && activeTab !== 'security'" class="flex flex-col gap-3 border-t border-slate-700/60 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <p class="text-xs text-slate-500">
          Изменения сохраняются только после нажатия кнопки.
        </p>
        <button
          type="button"
          class="inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="saving || !hasProfileChanges"
          @click="saveProfile"
        >
          <span v-if="saving" class="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
          {{ saving ? 'Сохранение...' : 'Сохранить изменения' }}
        </button>
      </div>
    </section>
  </div>
</template>
