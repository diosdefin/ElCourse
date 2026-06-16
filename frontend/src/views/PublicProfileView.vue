<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import api from '../api'
import Heatmap from '../components/Heatmap.vue'
import { useAuthStore } from '../stores/auth'
import { resolveMediaUrl } from '../utils/media'
import { showError, showSuccess } from '../utils/toast'

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
const isBioExpanded = ref(false)

const offerModal = ref({
  isOpen: false,
  message: '',
  contact: '',
  submitting: false,
  error: '',
})

const roleLabels = {
  student: 'Студент',
  teacher: 'Преподаватель',
  employer: 'Работодатель',
}

const getAvatarUrl = (avatar) => {
  if (!avatar) {
    return null
  }

  return resolveMediaUrl(avatar)
}

const roleLabel = computed(() => {
  const role = profile.value?.roles?.[0]
  return roleLabels[role] || 'Участник'
})

const isStudentProfile = computed(() => profile.value?.roles?.includes('student'))
const completedSkills = computed(() => profile.value?.skills || [])
const learningSkills = computed(() => profile.value?.learning_skills || [])
const bioText = computed(() => profile.value?.bio?.trim() || 'Пользователь пока не заполнил публичное описание.')
const canToggleBio = computed(() => bioText.value.length > 180)

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
    isBioExpanded.value = false
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
    showSuccess(response.data.message || 'Список друзей обновлён.')
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
    message: `Здравствуйте, ${profile.value.username}! Нам понравился ваш профиль на ElCourse, и мы хотели бы обсудить возможное сотрудничество.`,
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
    class="mx-auto mt-4 max-w-4xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="profile" class="mx-auto mt-1.5 max-w-5xl min-w-0 space-y-4 sm:mt-2.5 sm:space-y-5">
    <section class="max-w-full overflow-hidden rounded-[1.55rem] border border-slate-700/50 bg-slate-800/50 shadow-xl backdrop-blur-md">
      <div class="h-20 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.36),_transparent_35%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.14),_transparent_30%),linear-gradient(135deg,_rgba(15,23,42,1),_rgba(30,41,59,1))] sm:h-24"></div>
      <div class="px-4 pb-3.5 sm:px-5 sm:pb-4.5">
        <div class="-mt-10 flex flex-col gap-2.5 sm:-mt-12 sm:gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div class="flex min-w-0 items-center gap-2.5 sm:gap-3">
            <div class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-900 p-1 shadow-xl sm:h-24 sm:w-24">
              <img
                v-if="getAvatarUrl(profile.avatar)"
                :src="getAvatarUrl(profile.avatar)"
                :alt="profile.username"
                class="h-full w-full rounded-full object-cover"
              >
              <div
                v-else
                class="flex h-full w-full items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/20 text-3xl font-bold text-indigo-400"
              >
                {{ profile.username.charAt(0).toUpperCase() }}
              </div>
            </div>

            <div class="min-w-0 -translate-y-0.5 pb-0.5">
              <div class="flex flex-wrap items-center gap-2">
                <h1 class="break-words text-xl font-bold text-slate-100 sm:text-2xl">{{ profile.username }}</h1>
                <svg
                  v-if="profile.is_verified"
                  title="Верифицированный аккаунт"
                  class="h-5 w-5 rounded-full bg-white text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"></path>
                </svg>
              </div>

              <p class="mt-0.5 text-sm font-medium text-indigo-300">{{ roleLabel }}</p>
              <p class="mt-1 text-xs text-slate-500">На платформе с {{ profile.registration_year }}</p>
              <p class="mt-0.5 text-xs text-slate-500">{{ profile.friends_count }} друзей</p>
            </div>
          </div>

          <div class="flex w-full flex-wrap justify-end gap-2 lg:w-auto lg:self-start">
            <RouterLink
              v-if="profile.is_self"
              to="/profile"
              class="inline-flex min-h-[36px] items-center rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-semibold text-slate-100 transition hover:border-slate-500"
            >
              Мой профиль
            </RouterLink>

            <button
              v-else-if="canToggleFriend"
              class="inline-flex min-h-[36px] items-center rounded-full px-3 py-1.5 text-xs font-semibold text-white transition"
              :class="profile.is_friend
                ? 'bg-rose-600 hover:bg-rose-500'
                : 'bg-indigo-600 hover:bg-indigo-500'"
              :disabled="friendLoading"
              @click="toggleFriend"
            >
              {{ friendLoading ? 'Обновляем...' : profile.is_friend ? 'Убрать из друзей' : 'Добавить в друзья' }}
            </button>

            <button
              v-if="canDownloadResume"
              class="inline-flex min-h-[36px] items-center rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-semibold text-slate-100 transition hover:border-slate-500"
              :disabled="resumeLoading"
              @click="downloadResume"
            >
              {{ resumeLoading ? 'Готовим PDF...' : 'Резюме PDF' }}
            </button>

            <div
              v-if="offerStatusMeta"
              class="rounded-xl border px-3 py-2 text-xs font-semibold"
              :class="offerStatusMeta.className"
            >
              <p>{{ offerStatusMeta.title }}</p>
              <p class="mt-1 text-[11px] text-slate-500">{{ offerStatusMeta.subtitle }}</p>
            </div>

            <button
              v-else-if="canInvite"
              class="inline-flex min-h-[36px] items-center rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-500"
              @click="openOfferModal"
            >
              Пригласить
            </button>
          </div>
        </div>

        <div class="mt-2.5 max-w-3xl rounded-[1.15rem] border border-slate-700/50 bg-slate-900/55 p-3.5 sm:mt-3 sm:p-4">
          <div class="flex items-start justify-between gap-3">
            <h2 class="text-sm font-semibold text-slate-300">О себе</h2>
          </div>
          <p
            class="mt-2 break-words text-sm leading-6 text-slate-300"
            :class="isBioExpanded ? '' : 'line-clamp-3'"
          >
            {{ bioText }}
          </p>
          <div v-if="canToggleBio" class="mt-2 flex justify-end">
            <button
              class="text-xs font-medium text-indigo-300 transition hover:text-indigo-200"
              type="button"
              @click="isBioExpanded = !isBioExpanded"
            >
              {{ isBioExpanded ? 'Свернуть' : 'Ещё' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <Heatmap
      :activity-data="activityData"
      :selected-year="selectedYear"
      :available-years="availableYears"
      title="График активности"
      description="Годовой heatmap завершённых уроков и успешных Quiz."
      :error="activityError"
      @update:selected-year="selectedYear = $event"
    />

   <section
  v-if="isStudentProfile"
  class="max-w-full rounded-[1.35rem] border border-slate-700/45 bg-slate-800/45 p-3 shadow-xl backdrop-blur-md sm:p-4"
>
  <div class="flex items-center justify-between gap-3 border-b border-slate-700/60 pb-2.5">
    <div>
      <h2 class="text-base font-bold text-slate-100 sm:text-lg">Цифровой паспорт навыков</h2>
      <p class="mt-1 text-xs leading-5 text-slate-400">
        Навыки в обучении и уже подтверждённые результаты.
      </p>
    </div>
  </div>

  <div class="mt-3 grid gap-3 lg:grid-cols-2">
    <!-- В процессе изучения -->
    <div class="min-w-0 rounded-[1rem] border border-slate-700/45 bg-slate-950/45 p-3">
      <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-sm font-bold text-white">В процессе изучения</h3>
        <span class="rounded-full bg-indigo-500/10 px-2.5 py-1 text-xs font-bold text-indigo-300">
          {{ learningSkills.length }}
        </span>
      </div>

      <div v-if="learningSkills.length" class="flex flex-wrap gap-2">
        <div
          v-for="skill in learningSkills"
          :key="`${skill.course_name}-${skill.id}`"
          class="group relative inline-flex max-w-full items-center gap-2 overflow-hidden rounded-full border border-slate-700/70 bg-slate-900/80 px-3 py-1.5 text-xs font-bold text-slate-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
          :title="`${skill.name} — ${skill.progress_percentage}%`"
        >
          <span
            class="pointer-events-none absolute inset-y-0 left-0 rounded-full opacity-80 transition-all duration-500"
            :class="[
              skill.progress_percentage >= 70
                ? 'bg-emerald-500/25'
                : skill.progress_percentage >= 35
                  ? 'bg-amber-500/25'
                  : 'bg-rose-500/25'
            ]"
            :style="{ width: `${skill.progress_percentage}%` }"
          ></span>

          <span
            class="relative h-2 w-2 shrink-0 rounded-full"
            :class="[
              skill.progress_percentage >= 70
                ? 'bg-emerald-400'
                : skill.progress_percentage >= 35
                  ? 'bg-amber-400'
                  : 'bg-rose-400'
            ]"
          ></span>

          <span class="relative truncate">{{ skill.name }}</span>

          <span
            class="relative shrink-0 text-[11px]"
            :class="[
              skill.progress_percentage >= 70
                ? 'text-emerald-300'
                : skill.progress_percentage >= 35
                  ? 'text-amber-300'
                  : 'text-rose-300'
            ]"
          >
            {{ skill.progress_percentage }}%
          </span>
        </div>
      </div>

      <div v-else class="rounded-xl border border-dashed border-slate-700 px-3 py-3 text-xs text-slate-500">
        Пока нет навыков в процессе изучения.
      </div>
    </div>

    <!-- Подтверждённые -->
    <div class="min-w-0 rounded-[1rem] border border-slate-700/45 bg-slate-950/45 p-3">
      <div class="mb-3 flex items-center justify-between gap-3">
        <h3 class="text-sm font-bold text-white">Подтверждённые</h3>
        <span class="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-300">
          {{ completedSkills.length }}
        </span>
      </div>

      <div v-if="completedSkills.length" class="flex flex-wrap gap-2">
        <span
          v-for="skill in completedSkills"
          :key="skill.id"
          class="inline-flex max-w-full items-center gap-2 truncate rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-xs font-bold text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.08)]"
        >
          <svg class="h-3.5 w-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
          {{ skill.name }}
        </span>
      </div>

      <div v-else class="rounded-xl border border-dashed border-slate-700 px-3 py-3 text-xs text-slate-500">
        Подтверждённых навыков пока нет.
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
            <p class="text-xs font-bold uppercase tracking-[0.16em] text-indigo-300">Новый оффер</p>
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
