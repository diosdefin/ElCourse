<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { resolveMediaUrl } from '../utils/media'
import { showError, showSuccess } from '../utils/toast'

const WEEKDAY_LABELS = ['Вс', '', 'Вт', '', 'Чт', '', 'Сб']

const route = useRoute()
const authStore = useAuthStore()

const profile = ref(null)
const activityData = ref([])
const myOffers = ref([])
const loading = ref(true)
const pageError = ref('')
const activityError = ref('')
const selectedYear = ref(new Date().getFullYear())
const friendLoading = ref(false)
const resumeLoading = ref(false)
const syncingYear = ref(false)

const offerModal = ref({
  isOpen: false,
  message: '',
  contact: '',
  submitting: false,
  error: '',
})



const getAvatarUrl = (avatar) => {
  if (!avatar) {
    return null
  }

  return resolveMediaUrl(avatar)
}

const roleLabel = computed(() => {
  const role = profile.value?.roles?.[0]
  if (role === 'student') {
    return 'Студент'
  }

  if (role === 'teacher') {
    return 'Преподаватель'
  }

  if (role === 'employer') {
    return 'Работодатель'
  }

  return 'Участник'
})

const isStudentProfile = computed(() => profile.value?.roles?.includes('student'))
const completedSkills = computed(() => profile.value?.skills || [])
const learningSkills = computed(() => profile.value?.learning_skills || [])
const totalActivityCount = computed(() => activityData.value.reduce((sum, item) => sum + (item.count || 0), 0))

const availableYears = computed(() => {
  if (!profile.value?.registration_year) {
    return []
  }

  const currentYear = new Date().getFullYear()
  const years = []
  for (let year = currentYear; year >= profile.value.registration_year; year -= 1) {
    years.push(year)
  }
  return years
})

const activityMap = computed(() => {
  const mapped = new Map()
  for (const item of activityData.value) {
    mapped.set(item.date, item.count)
  }
  return mapped
})

const formatDateToIso = (date) => {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getActivityLevelClass = (count, inYear) => {
  if (!inYear) {
    return 'bg-slate-950/20'
  }

  if (count >= 5) {
    return 'bg-emerald-400'
  }

  if (count >= 3) {
    return 'bg-emerald-600'
  }

  if (count >= 1) {
    return 'bg-emerald-900'
  }

  return 'bg-slate-800'
}

const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'short' })

const heatmap = computed(() => {
  if (!selectedYear.value) {
    return { weeks: [], monthLabels: {} }
  }

  const startOfYear = new Date(selectedYear.value, 0, 1)
  const endOfYear = new Date(selectedYear.value, 11, 31)

  const gridStart = new Date(startOfYear)
  gridStart.setDate(gridStart.getDate() - gridStart.getDay())

  const gridEnd = new Date(endOfYear)
  gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()))

  const weeks = []
  const monthLabels = {}
  let cursor = new Date(gridStart)
  let lastMonth = ''
  let weekIndex = 0

  while (cursor <= gridEnd) {
    const week = []

    for (let day = 0; day < 7; day += 1) {
      const currentDate = new Date(cursor)
      const isoDate = formatDateToIso(currentDate)
      const inYear = currentDate.getFullYear() === selectedYear.value
      const count = inYear ? activityMap.value.get(isoDate) || 0 : 0

      week.push({
        date: isoDate,
        count,
        inYear,
        levelClass: getActivityLevelClass(count, inYear),
        title: inYear ? `${isoDate}: ${count} активностей` : '',
      })

      cursor.setDate(cursor.getDate() + 1)
    }

    const labelSource = week.find((item) => item.inYear && item.date.endsWith('-01')) || week.find((item) => item.inYear)
    if (labelSource) {
      const label = monthFormatter.format(new Date(labelSource.date))
      if (label !== lastMonth) {
        monthLabels[weekIndex] = label
        lastMonth = label
      }
    }

    weeks.push(week)
    weekIndex += 1
  }

  return { weeks, monthLabels }
})

const latestOffer = computed(() => {
  if (!profile.value) {
    return null
  }

  return myOffers.value.find((offer) => offer.student === profile.value.id) || null
})

const offerStatusMeta = computed(() => {
  if (!latestOffer.value) {
    return null
  }

  if (latestOffer.value.status === 'pending') {
    return {
      title: 'Оффер уже отправлен',
      subtitle: 'Ожидает ответа',
      className: 'border-slate-700 bg-slate-950 text-slate-300',
    }
  }

  if (latestOffer.value.status === 'accepted') {
    return {
      title: 'Оффер принят',
      subtitle: 'Повторная отправка не нужна',
      className: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    }
  }

  return null
})

const canToggleFriend = computed(() => authStore.isAuthenticated && !profile.value?.is_self)
const canInvite = computed(() => authStore.isEmployer && isStudentProfile.value && !profile.value?.is_self && !offerStatusMeta.value)
const canDownloadResume = computed(
  () => authStore.isAuthenticated && isStudentProfile.value && (authStore.isEmployer || profile.value?.is_self)
)

const fetchEmployerOffers = async () => {
  if (!authStore.isEmployer || !profile.value || !isStudentProfile.value || profile.value.is_self) {
    myOffers.value = []
    return
  }
  try {
    const response = await api.get('/employer/offers/')
    myOffers.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки офферов работодателя:', error)
    myOffers.value = []
  }
}

const fetchProfile = async (username) => {
  loading.value = true
  pageError.value = ''
  activityError.value = ''
  try {
    const response = await api.get(`/users/${username}/`)
    profile.value = response.data
    syncingYear.value = true
    selectedYear.value = new Date().getFullYear()
    await fetchActivity()
    syncingYear.value = false
    await fetchEmployerOffers()
  } catch (error) {
    console.error('Ошибка загрузки публичного профиля:', error)
    pageError.value = 'Не удалось открыть публичный профиль. Возможно, пользователь не найден.'
  } finally {
    loading.value = false
  }
}

const fetchActivity = async () => {
  if (!route.params.username || !selectedYear.value) {
    activityData.value = []
    return
  }
  activityError.value = ''
  try {
    const response = await api.get(`/users/${route.params.username}/activity/`, {
      params: { year: selectedYear.value },
    })
    activityData.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки активности:', error)
    activityData.value = []
    activityError.value = error.response?.data?.detail || 'Не удалось загрузить активность за выбранный год.'
  }
}

const toggleFriend = async () => {
  if (!profile.value || !canToggleFriend.value) {
    return
  }
  friendLoading.value = true
  try {
    const response = await api.post(`/users/${profile.value.username}/friend/`, {})
    profile.value = {
      ...profile.value,
      is_friend: response.data.is_friend,
      friends_count: response.data.friends_count,
    }
    showSuccess(response.data.message || 'Список друзей обновлен.')
  } catch (error) {
    console.error('Ошибка обновления друзей:', error)
    showError(error.response?.data?.detail || 'Не удалось обновить друзей.')
  } finally {
    friendLoading.value = false
  }
}

const downloadResume = async () => {
  if (!profile.value || !canDownloadResume.value) {
    return
  }
  resumeLoading.value = true
  try {
    const response = await api.get('/resume/export/', {
      params: { user_id: profile.value.id },
      responseType: 'blob',
    })
    const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = blobUrl
    link.setAttribute('download', `Resume_${profile.value.username}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrl)
  } catch (error) {
    console.error('Ошибка скачивания резюме:', error)
    showError('Не удалось скачать PDF-резюме.')
  } finally {
    resumeLoading.value = false
  }
}

const openOfferModal = () => {
  if (!profile.value || !canInvite.value) {
    return
  }

  offerModal.value = {
    isOpen: true,
    message: `Здравствуйте, ${profile.value.username}! Нам понравился ваш профиль на ELCOURSE и мы хотели бы обсудить возможное сотрудничество.`,
    contact: '',
    submitting: false,
    error: '',
  }
}

const closeOfferModal = () => {
  offerModal.value = {
    isOpen: false,
    message: '',
    contact: '',
    submitting: false,
    error: '',
  }
}

const submitOffer = async () => {
  if (!profile.value || !offerModal.value.message.trim()) {
    return
  }
  offerModal.value.submitting = true
  offerModal.value.error = ''
  try {
    await api.post('/employer/offer/', {
      student_id: profile.value.id,
      message: offerModal.value.message.trim(),
      contact_link: offerModal.value.contact.trim(),
    })
    closeOfferModal()
    await fetchEmployerOffers()
    showSuccess('Оффер отправлен.')
  } catch (error) {
    console.error('Ошибка отправки оффера:', error)
    offerModal.value.error =
      error.response?.data?.detail || 'Не удалось отправить оффер. Попробуйте еще раз.'
    if (error.response?.data?.existing_offer) {
      await fetchEmployerOffers()
    }
  } finally {
    offerModal.value.submitting = false
  }
}

watch(
  () => route.params.username,
  (username) => {
    if (typeof username === 'string' && username.trim()) {
      fetchProfile(username)
    }
  },
  { immediate: true }
)

watch(selectedYear, () => {
  if (profile.value && !syncingYear.value) {
    fetchActivity()
  }
})
</script>

<template>
  <div v-if="loading" class="flex h-64 items-center justify-center">
    <div class="text-lg text-slate-400">Открываем профиль...</div>
  </div>

  <div
    v-else-if="pageError"
    class="mx-auto mt-8 max-w-4xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="profile" class="mx-auto mt-8 max-w-7xl max-w-full min-w-0 space-y-8">
    <section class="max-w-full overflow-hidden rounded-[2rem] border border-slate-700/50 bg-slate-800/50 shadow-xl backdrop-blur-md">
      <div class="h-40 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.36),_transparent_35%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.14),_transparent_30%),linear-gradient(135deg,_rgba(15,23,42,1),_rgba(30,41,59,1))]"></div>
      <div class="px-4 pb-6 sm:px-8 sm:pb-8">
        <div class="-mt-16 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="flex min-w-0 items-end gap-4 sm:gap-5">
            <div class="flex h-32 w-32 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-900 p-1.5 shadow-xl">
              <img
                v-if="getAvatarUrl(profile.avatar)"
                :src="getAvatarUrl(profile.avatar)"
                :alt="profile.username"
                class="h-full w-full rounded-full object-cover"
              >
              <div
                v-else
                class="flex h-full w-full items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/20 text-4xl font-bold text-indigo-400"
              >
                {{ profile.username.charAt(0).toUpperCase() }}
              </div>
            </div>

            <div class="min-w-0 pb-2">
              <div class="flex items-center gap-3">
                <h1 class="break-words text-2xl font-bold text-slate-100 sm:text-4xl">{{ profile.username }}</h1>
                <svg
                  v-if="profile.is_verified"
                  title="Верифицированный аккаунт"
                  class="h-7 w-7 rounded-full bg-white text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"></path>
                </svg>
              </div>

              <p class="mt-2 font-medium text-indigo-300">{{ roleLabel }}</p>
              <div class="mt-4 flex flex-wrap gap-3 text-sm text-slate-400">
                <span class="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1">
                  На платформе с {{ profile.registration_year }}
                </span>
                <span class="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1">
                  {{ profile.friends_count }} друзей
                </span>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
            <RouterLink
              v-if="profile.is_self"
              to="/profile"
              class="w-full rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-bold text-slate-100 transition hover:border-slate-500 sm:w-auto"
            >
              Перейти в мой профиль
            </RouterLink>

            <button
              v-else-if="canToggleFriend"
              class="w-full rounded-xl px-5 py-3 text-sm font-bold text-white transition sm:w-auto"
              :class="profile.is_friend
                ? 'bg-rose-600 hover:bg-rose-500'
                : 'bg-indigo-600 hover:bg-indigo-500'"
              :disabled="friendLoading"
              @click="toggleFriend"
            >
              {{ friendLoading ? 'Обновляем...' : profile.is_friend ? 'Удалить из друзей' : 'Добавить в друзья' }}
            </button>

            <button
              v-if="canDownloadResume"
              class="w-full rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-bold text-slate-100 transition hover:border-slate-500 sm:w-auto"
              :disabled="resumeLoading"
              @click="downloadResume"
            >
              {{ resumeLoading ? 'Готовим PDF...' : 'Скачать резюме (PDF)' }}
            </button>

            <div
              v-if="offerStatusMeta"
              class="rounded-xl border px-5 py-3 text-sm font-semibold"
              :class="offerStatusMeta.className"
            >
              <p>{{ offerStatusMeta.title }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ offerStatusMeta.subtitle }}</p>
            </div>

            <button
              v-else-if="canInvite"
              class="w-full rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-500 sm:w-auto"
              @click="openOfferModal"
            >
              Пригласить
            </button>
          </div>
        </div>

        <div class="mt-6 rounded-2xl border border-slate-700/50 bg-slate-900/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-slate-400">О себе</h3>
          <p class="break-words leading-relaxed text-slate-300">
            {{ profile.bio || 'Пользователь пока не заполнил публичное описание.' }}
          </p>
        </div>
      </div>
    </section>

    <section class="max-w-full rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-4 shadow-xl backdrop-blur-md sm:p-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="min-w-0">
          <h2 class="text-2xl font-bold text-slate-100">График активности</h2>
          <p class="mt-2 text-sm text-slate-400">
            Годовой heatmap завершенных уроков и успешных Quiz.
          </p>
        </div>

        <div class="self-start rounded-2xl border border-slate-700 bg-slate-900/50 px-4 py-3 text-left xl:text-right">
          <p class="text-xs uppercase tracking-[0.25em] text-slate-500">Активностей за год</p>
          <p class="mt-2 text-2xl font-black text-white">{{ totalActivityCount }}</p>
        </div>
      </div>

      <div class="mt-6 grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr),92px]">
        <div class="min-w-0 overflow-hidden rounded-3xl border border-slate-700/50 bg-slate-900/50 p-4">
          <div class="max-w-full overflow-x-auto pb-2">
            <div class="inline-flex min-w-max gap-2 sm:gap-3">
              <div class="pt-5 text-[9px] text-slate-500 sm:pt-7 sm:text-[10px]">
                <div
                  v-for="(label, index) in WEEKDAY_LABELS"
                  :key="index"
                  class="flex h-3 items-center sm:h-4"
                >
                  {{ label }}
                </div>
              </div>

              <div class="min-w-0">
                <div class="mb-2 flex gap-0.5 text-[9px] uppercase tracking-[0.12em] text-slate-500 sm:gap-1 sm:text-[10px] sm:tracking-[0.2em]">
                  <div
                    v-for="(week, index) in heatmap.weeks"
                    :key="`month-${index}`"
                    class="w-3 sm:w-4"
                  >
                    {{ heatmap.monthLabels[index] || '' }}
                  </div>
                </div>

                <div class="flex gap-0.5 sm:gap-1">
                  <div
                    v-for="(week, weekIndex) in heatmap.weeks"
                    :key="`week-${weekIndex}`"
                    class="flex flex-col gap-0.5 sm:gap-1"
                  >
                    <div
                      v-for="day in week"
                      :key="day.date"
                      class="h-3 w-3 rounded-[3px] transition-transform sm:h-4 sm:w-4 sm:rounded-[4px] sm:hover:scale-125"
                      :class="day.levelClass"
                      :title="day.title"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
            <p>Меньше</p>
            <div class="flex items-center gap-2">
              <span class="h-3 w-3 rounded-[4px] bg-slate-800"></span>
              <span class="h-3 w-3 rounded-[4px] bg-emerald-900"></span>
              <span class="h-3 w-3 rounded-[4px] bg-emerald-600"></span>
              <span class="h-3 w-3 rounded-[4px] bg-emerald-400"></span>
            </div>
            <p>Больше</p>
          </div>

          <p v-if="activityError" class="mt-4 text-sm text-amber-400">{{ activityError }}</p>
        </div>

        <div class="min-w-0 rounded-3xl border border-slate-700/50 bg-slate-900/50 p-3">
          <p class="px-2 text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Год</p>
          <div class="mt-3 space-y-2">
            <button
              v-for="year in availableYears"
              :key="year"
              class="w-full rounded-2xl px-3 py-2 text-sm font-bold transition"
              :class="selectedYear === year
                ? 'bg-white text-slate-950'
                : 'bg-slate-950 text-slate-300 hover:bg-slate-800 hover:text-white'"
              @click="selectedYear = year"
            >
              {{ year }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section
      v-if="isStudentProfile"
      class="max-w-full rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-4 shadow-xl backdrop-blur-md sm:p-8"
    >
      <h2 class="border-b border-slate-700 pb-4 text-2xl font-bold text-slate-100">
        Цифровой паспорт навыков
      </h2>

      <div class="mt-8 grid gap-6 xl:grid-cols-2">
        <div class="min-w-0 rounded-3xl border border-slate-700/50 bg-slate-900/50 p-6">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <h3 class="text-lg font-bold text-white">В процессе изучения</h3>
              <p class="mt-1 text-sm text-slate-400">Навыки, которые открываются по мере прохождения уроков.</p>
            </div>
            <span class="rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-300">
              {{ learningSkills.length }}
            </span>
          </div>

          <div v-if="learningSkills.length" class="mt-6 space-y-4">
            <div
              v-for="skill in learningSkills"
              :key="`${skill.course_name}-${skill.id}`"
              class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4"
            >
              <div class="mb-3 flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="break-words font-bold text-slate-100">{{ skill.name }}</p>
                  <p class="mt-1 break-words text-sm text-slate-500">{{ skill.course_name }}</p>
                </div>
                <span class="text-sm font-bold text-emerald-300">{{ skill.progress_percentage }}%</span>
              </div>

              <div class="h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                  class="h-full rounded-full bg-gradient-to-r from-indigo-600 to-emerald-500 transition-all duration-500"
                  :style="{ width: `${skill.progress_percentage}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div
            v-else
            class="mt-6 rounded-2xl border border-dashed border-slate-700 p-6 text-sm text-slate-500"
          >
            Навыков в процессе изучения пока нет.
          </div>
        </div>

        <div class="min-w-0 rounded-3xl border border-slate-700/50 bg-slate-900/50 p-6">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <h3 class="text-lg font-bold text-white">Подтвержденные</h3>
              <p class="mt-1 text-sm text-slate-400">Навыки, закрепленные после прохождения Quiz.</p>
            </div>
            <span class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-300">
              {{ completedSkills.length }}
            </span>
          </div>

          <div v-if="completedSkills.length" class="mt-6 flex flex-wrap gap-3">
            <span
              v-for="skill in completedSkills"
              :key="skill.id"
              class="flex max-w-full items-center gap-2 break-words rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
            >
              <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
              </svg>
              {{ skill.name }}
            </span>
          </div>

          <div
            v-else
            class="mt-6 rounded-2xl border border-dashed border-slate-700 p-6 text-sm text-slate-500"
          >
            Подтвержденных навыков пока нет.
          </div>
        </div>
      </div>
    </section>

    <div
      v-if="offerModal.isOpen"
      class="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/85 p-3 backdrop-blur-md sm:p-4"
      @click.self="closeOfferModal"
    >
      <div class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[2rem] border border-slate-700 bg-slate-900 p-5 shadow-2xl shadow-black/60 sm:p-8">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div class="min-w-0">
            <p class="text-xs font-bold uppercase tracking-[0.25em] text-indigo-300">Новый оффер</p>
            <h2 class="mt-3 break-words text-2xl font-black text-white sm:text-3xl">Приглашение для {{ profile.username }}</h2>
            <p class="mt-3 text-sm leading-6 text-slate-400">
              Студент увидит приглашение в уведомлениях, а профиль сразу покажет статус оффера.
            </p>
          </div>

          <button class="self-start text-slate-500 transition hover:text-white" @click="closeOfferModal">
            <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="mt-8 space-y-5">
          <div>
            <label class="mb-2 block text-sm font-bold text-slate-300">Сообщение</label>
            <textarea
              v-model="offerModal.message"
              rows="5"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-5 py-4 text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
              placeholder="Расскажите, чем заинтересовал профиль и как продолжить общение..."
            ></textarea>
          </div>

          <div>
            <label class="mb-2 block text-sm font-bold text-slate-300">Контакт</label>
            <input
              v-model="offerModal.contact"
              type="text"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-5 py-4 text-slate-100 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/30"
              placeholder="t.me/hr_manager или email@company.com"
            >
          </div>

          <div
            v-if="offerModal.error"
            class="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300"
          >
            {{ offerModal.error }}
          </div>
        </div>

        <div class="mt-8 grid gap-3 sm:grid-cols-2">
          <button
            class="rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
            @click="closeOfferModal"
          >
            Отмена
          </button>
          <button
            class="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="offerModal.submitting || !offerModal.message.trim()"
            @click="submitOffer"
          >
            {{ offerModal.submitting ? 'Отправляем...' : 'Отправить оффер' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
