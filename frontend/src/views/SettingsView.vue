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
  { key: 'basic', label: 'Основное' },
  { key: 'contacts', label: 'Контакты' },
  { key: 'security', label: 'Безопасность' },
]

const activeTab = ref('basic')
const loading = ref(true)
const saving = ref(false)
const changingPassword = ref(false)
const avatarPreview = ref(null)

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
  if (!value) {
    return ''
  }
  return `${value}`.replace(/[<>]/g, '').trim()
}

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
  avatarPreview.value = data.avatar
}

const isDangerous = (value) => /<script|javascript:|onerror=|onload=/i.test(value || '')

const hasProfileChanges = computed(() => {
  if (!originalData.value) {
    return false
  }

  if (form.avatar) {
    return true
  }

  return (
    sanitizeText(form.bio) !== originalData.value.bio ||
    sanitizeText(form.location) !== originalData.value.location ||
    sanitizeText(form.telegram) !== originalData.value.telegram ||
    sanitizeText(form.github) !== originalData.value.github ||
    sanitizeText(form.linkedin) !== originalData.value.linkedin
  )
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
  if (!file) {
    return
  }

  // Валидация типа и размера
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
  if (!allowedTypes.includes(file.type)) {
    showError('Можно загружать только JPEG, PNG или WEBP изображения.')
    event.target.value = ''
    return
  }

  const maxSize = 2 * 1024 * 1024 // 2 MB
  if (file.size > maxSize) {
    showError('Размер аватара не должен превышать 2 МБ.')
    event.target.value = ''
    return
  }

  form.avatar = file
  avatarPreview.value = URL.createObjectURL(file)
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

  if (form.avatar) {
    payload.avatar = form.avatar
  }

  return payload
}

const saveProfile = async () => {
  if (!originalData.value) {
    return
  }

  for (const fieldName of ['telegram', 'github', 'linkedin']) {
    if (isDangerous(form[fieldName])) {
      showError(`Поле ${fieldName} содержит потенциально опасный код.`)
      return
    }
  }

  const patchPayload = buildPatchPayload()
  const keys = Object.keys(patchPayload)
  if (!keys.length) {
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
    showSuccess('Изменения сохранены.')
  } catch (error) {
    console.error('Ошибка сохранения профиля:', error)
    const detail = error.response?.data

    if (detail?.avatar?.[0]) {
      showError(detail.avatar[0])
      return
    }

    if (detail?.detail) {
      showError(detail.detail)
      return
    }

    showError('Не удалось сохранить изменения. Попробуйте ещё раз.')
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
  <div class="mx-auto mt-8 max-w-5xl space-y-6 px-4">
    <section class="rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-8 shadow-xl backdrop-blur-md">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 class="text-3xl font-black text-slate-100">Настройки профиля</h1>
          <p class="mt-2 text-sm text-slate-400">Управляйте личными данными, контактами и безопасностью.</p>
        </div>
      </div>
    </section>

    <section class="rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-6 shadow-xl backdrop-blur-md">
      <div class="border-b border-slate-700/60">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="rounded-t-xl px-4 py-2 text-sm font-semibold transition"
            :class="activeTab === tab.key
              ? 'border-b-2 border-indigo-400 bg-slate-900/70 text-indigo-300'
              : 'text-slate-400 hover:bg-slate-900/40 hover:text-slate-200'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="flex h-52 items-center justify-center">
        <div class="h-10 w-10 animate-spin rounded-full border-b-2 border-indigo-400"></div>
      </div>

      <div v-else class="mt-6 space-y-6">
        <template v-if="activeTab === 'basic'">
          <div class="grid gap-6 lg:grid-cols-[220px,1fr]">
            <div class="space-y-4">
              <div class="h-44 w-44 overflow-hidden rounded-2xl border border-slate-700 bg-slate-900">
                <img v-if="avatarPreview" :src="avatarPreview" alt="Avatar" class="h-full w-full object-cover">
                <div v-else class="flex h-full w-full items-center justify-center text-4xl font-black text-slate-600">
                  {{ form.username?.[0]?.toUpperCase() || 'U' }}
                </div>
              </div>

              <label class="inline-flex cursor-pointer items-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500">
                Загрузить аватар
                <input type="file" class="hidden" accept="image/*" @change="onAvatarChange">
              </label>
            </div>

            <div class="space-y-4">
              <div class="grid gap-4 sm:grid-cols-2">
                <div class="rounded-xl border border-slate-700 bg-slate-900/50 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.2em] text-slate-500">Username</p>
                  <p class="mt-1 text-sm font-semibold text-slate-200">{{ form.username }}</p>
                </div>
                <div class="rounded-xl border border-slate-700 bg-slate-900/50 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.2em] text-slate-500">Email</p>
                  <p class="mt-1 text-sm font-semibold text-slate-200">{{ form.email }}</p>
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-300">О себе</label>
                <textarea
                  v-model="form.bio"
                  rows="5"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
                  placeholder="Расскажите немного о себе"
                ></textarea>
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-300">Локация</label>
                <input
                  v-model="form.location"
                  type="text"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
                  placeholder="Например: Москва"
                >
              </div>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'contacts'">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-300">Telegram</label>
              <input
                v-model="form.telegram"
                type="text"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
                placeholder="@username"
              >
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-300">GitHub</label>
              <input
                v-model="form.github"
                type="text"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
                placeholder="username или ссылка"
              >
            </div>

            <div class="md:col-span-2">
              <label class="mb-2 block text-sm font-semibold text-slate-300">LinkedIn</label>
              <input
                v-model="form.linkedin"
                type="text"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
                placeholder="username или ссылка"
              >
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'security'">
          <div class="max-w-2xl space-y-4">
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-300">Старый пароль</label>
              <input
                v-model="passwordForm.old_password"
                type="password"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
              >
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-300">Новый пароль</label>
              <input
                v-model="passwordForm.new_password"
                type="password"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
              >
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-300">Подтверждение нового пароля</label>
              <input
                v-model="passwordForm.confirm_password"
                type="password"
                class="w-full rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-slate-200 outline-none transition focus:border-indigo-400"
              >
            </div>

            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="changingPassword"
              @click="changeUserPassword"
            >
              <span
                v-if="changingPassword"
                class="h-4 w-4 animate-spin rounded-full border-b-2 border-white"
              ></span>
              Сменить пароль
            </button>
          </div>
        </template>
      </div>

      <div class="mt-8 border-t border-slate-700/60 pt-5">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="saving || !hasProfileChanges"
          @click="saveProfile"
        >
          <span v-if="saving" class="h-4 w-4 animate-spin rounded-full border-b-2 border-white"></span>
          Сохранить изменения
        </button>
      </div>
    </section>
  </div>
</template>