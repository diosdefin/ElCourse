<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import api, { getTeacherActivity } from '../api'
import Heatmap from '../components/Heatmap.vue'
import { resolveMediaUrl } from '../utils/media'
import { showError } from '../utils/toast'

const userData = ref(null)
const activityData = ref([])
const selectedYear = ref(new Date().getFullYear())
const loading = ref(true)
const pageError = ref('')
const activityError = ref('')
const syncingYear = ref(false)
const isBioExpanded = ref(false)

const roleLabels = {
  student: 'Студент',
  teacher: 'Преподаватель',
  employer: 'Работодатель',
}

const getAvatarUrl = (avatar) => {
  if (!avatar) return '/default-avatar.png'
  return resolveMediaUrl(avatar)
}

const completedSkills = computed(() => userData.value?.completed_skills || [])
const learningSkills = computed(() => userData.value?.learning_skills || [])
const isTeacherProfile = computed(() => userData.value?.role === 'teacher')
const isStudentProfile = computed(() => userData.value?.role === 'student')
const roleLabel = computed(() => roleLabels[userData.value?.role] || 'Пользователь')
const showActivityHeatmap = computed(() => ['student', 'teacher'].includes(userData.value?.role))
const activityTitle = computed(() => (isTeacherProfile.value ? 'Активность автора' : 'График активности'))
const activityDescription = computed(() =>
  isTeacherProfile.value
    ? 'Годовой heatmap созданных курсов, уроков, загруженных HLS-видео и обновлений Quiz.'
    : 'Годовой heatmap завершённых уроков и успешных Quiz.'
)
const bioText = computed(() => userData.value?.bio?.trim() || 'Информация пока не заполнена.')
const canToggleBio = computed(() => bioText.value.length > 180)

const availableYears = computed(() => {
  if (!userData.value?.registration_year) return []
  const currentYear = new Date().getFullYear()
  const years = []
  for (let year = currentYear; year >= userData.value.registration_year; year -= 1) {
    years.push(year)
  }
  return years
})

const fetchActivity = async () => {
  if (!userData.value || !selectedYear.value) return
  activityError.value = ''

  try {
    const response = isTeacherProfile.value
      ? await getTeacherActivity(selectedYear.value)
      : await api.get('/me/activity/', {
        params: { year: selectedYear.value },
      })
    activityData.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки активности:', error)
    activityData.value = []
    activityError.value = error.response?.data?.detail || 'Не удалось загрузить активность за выбранный год.'
  }
}

const fetchProfile = async () => {
  loading.value = true
  pageError.value = ''
  activityError.value = ''

  try {
    const response = await api.get('/me/')
    userData.value = response.data
    isBioExpanded.value = false
    syncingYear.value = true
    await fetchActivity()
    syncingYear.value = false
  } catch (error) {
    console.error('Ошибка загрузки профиля:', error)
    pageError.value = 'Не удалось загрузить профиль. Попробуйте обновить страницу.'
  } finally {
    loading.value = false
  }
}

const downloadResume = async () => {
  try {
    const response = await api.get('/resume/export/', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `Resume_${userData.value.username}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Ошибка при скачивании PDF:', error)
    showError('Не удалось сгенерировать резюме.')
  }
}

watch(selectedYear, () => {
  if (userData.value && !syncingYear.value) {
    fetchActivity()
  }
})

onMounted(fetchProfile)
</script>

<template>
  <div v-if="loading" class="flex h-64 items-center justify-center">
    <div class="text-lg text-slate-400">Загрузка профиля...</div>
  </div>

  <div
    v-else-if="pageError"
    class="mx-auto mt-4 max-w-4xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="userData" class="mx-auto mt-1.5 max-w-5xl min-w-0 space-y-4 sm:mt-2.5 sm:space-y-5">
    <section class="max-w-full overflow-hidden rounded-[1.55rem] border border-slate-700/50 bg-slate-800/50 shadow-xl backdrop-blur-md">
      <div class="h-20 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.38),_transparent_35%),linear-gradient(135deg,_rgba(15,23,42,1),_rgba(30,41,59,1))] sm:h-24"></div>
      <div class="px-4 pb-3.5 sm:px-5 sm:pb-4.5">
        <div class="-mt-10 flex flex-col gap-2.5 sm:-mt-12 sm:gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div class="flex min-w-0 items-center gap-2.5 sm:gap-3">
            <div class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-900 p-1 shadow-xl sm:h-24 sm:w-24">
              <img
                v-if="getAvatarUrl(userData?.avatar)"
                :src="getAvatarUrl(userData?.avatar)"
                :alt="userData.username"
                class="h-full w-full rounded-full object-cover"
              >
              <div
                v-else
                class="flex h-full w-full items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/20 text-2xl font-bold text-indigo-400 sm:text-3xl"
              >
                {{ userData.username.charAt(0).toUpperCase() }}
              </div>
            </div>

            <div class="min-w-0 -translate-y-0.5 pb-0.5">
              <div class="flex flex-wrap items-center gap-2">
                <h1 class="break-words text-xl font-bold text-slate-100 sm:text-2xl">{{ userData.username }}</h1>
                <svg
                  v-if="userData.is_verified"
                  title="Верифицированный аккаунт"
                  class="h-5 w-5 rounded-full bg-white text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"></path>
                </svg>
              </div>

              <p class="mt-0.5 text-sm font-medium text-indigo-300">{{ roleLabel }}</p>
              <p class="mt-0.5 break-all text-sm text-slate-400">{{ userData.email }}</p>
              <p class="mt-1 text-xs text-slate-500">На платформе с {{ userData.registration_year }}</p>
            </div>
          </div>

          <div class="flex w-full flex-wrap justify-end gap-2 lg:w-auto lg:self-start">
            <button
              v-if="isStudentProfile"
              class="inline-flex min-h-[36px] items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-semibold text-slate-100 transition hover:border-slate-500 hover:text-white"
              @click="downloadResume"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v10m-3-3 3 3 3-3" />
              </svg>
              Резюме PDF
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
      v-if="showActivityHeatmap"
      :activity-data="activityData"
      :selected-year="selectedYear"
      :available-years="availableYears"
      :title="activityTitle"
      :description="activityDescription"
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
  </div>
</template>
