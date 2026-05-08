<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import api, { getTeacherActivity } from '../api'
import { showError, showSuccess } from '../utils/toast'

const API_BASE_URL = 'http://127.0.0.1:8000'
const WEEKDAY_LABELS = ['Вс', '', 'Вт', '', 'Чт', '', 'Сб']   // НОВОЕ

const userData = ref(null)
const activityData = ref([])
const selectedYear = ref(new Date().getFullYear())            // НОВОЕ
const loading = ref(true)
const pageError = ref('')
const activityError = ref('')
const isEditing = ref(false)
const saving = ref(false)
const editData = ref({
  bio: '',
  avatarFile: null,
})
const syncingYear = ref(false)                                 // НОВОЕ

// ========== НОВЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
const formatDateToIso = (date) => {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getActivityLevelClass = (count, inYear = true) => {
  if (!inYear) return 'bg-slate-950/20'
  if (count >= 5) return 'bg-emerald-400'
  if (count >= 3) return 'bg-emerald-600'
  if (count >= 1) return 'bg-emerald-900'
  return 'bg-slate-800'
}

const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'short' })
// ====================================================

const getAvatarUrl = (avatar) => {
  if (!avatar) return null
  return avatar.startsWith('http') ? avatar : `${API_BASE_URL}${avatar}`
}

const completedSkills = computed(() => userData.value?.completed_skills || [])
const learningSkills = computed(() => userData.value?.learning_skills || [])
const isTeacherProfile = computed(() => userData.value?.role === 'teacher')
const showActivityHeatmap = computed(() => ['student', 'teacher'].includes(userData.value?.role))
const activityTitle = computed(() => (isTeacherProfile.value ? 'Активность автора' : 'График активности'))
const activityDescription = computed(() =>
  isTeacherProfile.value
    ? 'Годовой heatmap созданных курсов, уроков, загруженных HLS-видео и обновлений Quiz.'
    : 'Годовой heatmap завершенных уроков и успешных Quiz.'
)

// НОВОЕ: вычисляем общее количество активностей за выбранный год
const totalActivityCount = computed(() =>
  activityData.value.reduce((sum, item) => {
    if (!item.date?.startsWith(`${selectedYear.value}-`)) return sum
    return sum + (item.count || 0)
  }, 0)
)

// НОВОЕ: карта дата -> количество
const activityMap = computed(() => {
  const map = new Map()
  for (const item of activityData.value) {
    map.set(item.date, item.count)
  }
  return map
})

// НОВОЕ: построение тепловой карты (недели, ячейки, подписи месяцев)
const heatmap = computed(() => {
  if (!selectedYear.value) return { weeks: [], monthLabels: {} }

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
    for (let day = 0; day < 7; day++) {
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
    const labelSource = week.find(item => item.inYear && item.date.endsWith('-01')) || week.find(item => item.inYear)
    if (labelSource) {
      const label = monthFormatter.format(new Date(labelSource.date))
      if (label !== lastMonth) {
        monthLabels[weekIndex] = label
        lastMonth = label
      }
    }
    weeks.push(week)
    weekIndex++
  }
  return { weeks, monthLabels }
})

// НОВОЕ: список доступных лет (от года регистрации до текущего)
const availableYears = computed(() => {
  if (!userData.value?.registration_year) return []
  const currentYear = new Date().getFullYear()
  const years = []
  for (let y = currentYear; y >= userData.value.registration_year; y--) {
    years.push(y)
  }
  return years
})

// ========== ЗАГРУЗКА ПРОФИЛЯ И АКТИВНОСТИ ==========
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
    const profileResult = await api.get('/me/')
    userData.value = profileResult.data
    editData.value.bio = profileResult.data.bio || ''
    // Загружаем активность за текущий год
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

// ========== РЕДАКТИРОВАНИЕ ПРОФИЛЯ ==========
const startEditing = () => {
  if (!userData.value) return
  isEditing.value = true
  editData.value.bio = userData.value.bio || ''
  editData.value.avatarFile = null
}

const onFileChange = (event) => {
  editData.value.avatarFile = event.target.files?.[0] || null
}

const saveProfile = async () => {
  saving.value = true
  try {
    const formData = new FormData()
    formData.append('bio', editData.value.bio)
    if (editData.value.avatarFile) {
      formData.append('avatar', editData.value.avatarFile)
    }
    const response = await api.patch('/profile/update/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (userData.value) {
      userData.value.bio = response.data.bio
      if (response.data.avatar) userData.value.avatar = response.data.avatar
    }
    isEditing.value = false
    showSuccess('Профиль успешно обновлен.')
  } catch (error) {
    console.error('Ошибка при сохранении профиля:', error)
    showError('Ошибка при сохранении профиля.')
  } finally {
    saving.value = false
  }
}

const cancelEditing = () => {
  isEditing.value = false
  editData.value.bio = userData.value?.bio || ''
  editData.value.avatarFile = null
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

// Следим за сменой года
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
    class="mx-auto mt-8 max-w-4xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="userData" class="mx-auto mt-8 max-w-6xl space-y-8">
    <!-- Шапка профиля (без изменений) -->
    <section class="overflow-hidden rounded-[2rem] border border-slate-700/50 bg-slate-800/50 shadow-xl backdrop-blur-md">
      <div class="h-36 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.38),_transparent_35%),linear-gradient(135deg,_rgba(15,23,42,1),_rgba(30,41,59,1))]"></div>
      <div class="px-8 pb-8">
        <div class="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between -mt-14">
          <div class="flex items-end gap-5">
            <div class="relative">
              <div class="flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-900 p-1.5 shadow-xl">
                <img
                  v-if="getAvatarUrl(userData.avatar)"
                  :src="getAvatarUrl(userData.avatar)"
                  :alt="userData.username"
                  class="h-full w-full rounded-full object-cover"
                >
                <div
                  v-else
                  class="flex h-full w-full items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/20 text-3xl font-bold text-indigo-400"
                >
                  {{ userData.username.charAt(0).toUpperCase() }}
                </div>
              </div>
              <div v-if="isEditing" class="absolute -bottom-2 -right-2">
                <label class="cursor-pointer rounded-full bg-indigo-600 p-2 shadow-lg transition-colors hover:bg-indigo-500">
                  <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  <input type="file" class="hidden" accept="image/*" @change="onFileChange" />
                </label>
              </div>
            </div>
            <div class="pb-1">
              <div class="flex items-center gap-3">
                <h1 class="text-3xl font-bold text-slate-100">{{ userData.username }}</h1>
                <svg
                  v-if="userData.is_verified"
                  title="Верифицированный аккаунт"
                  class="h-7 w-7 rounded-full bg-white text-blue-500"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"></path>
                </svg>
              </div>
              <p class="mt-1 font-medium text-indigo-400">
                <template v-if="userData.role === 'student'">Студент</template>
                <template v-else-if="userData.role === 'teacher'">Преподаватель</template>
                <template v-else-if="userData.role === 'employer'">Работодатель</template>
              </p>
              <p class="mt-2 text-slate-400">{{ userData.email }}</p>
            </div>
          </div>
          <div class="flex flex-wrap gap-3">
            <button
              v-if="userData.role === 'student' && !isEditing"
              class="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-bold text-white shadow-lg shadow-indigo-500/25 transition-all hover:bg-indigo-500"
              @click="downloadResume"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m-4-4l4 4 4-4" />
              </svg>
              Скачать резюме (PDF)
            </button>
            <button
              v-if="!isEditing"
              class="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 font-bold text-white shadow-lg shadow-emerald-500/25 transition-all hover:bg-emerald-500"
              @click="startEditing"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Редактировать профиль
            </button>
          </div>
        </div>
        <!-- Блок "О себе" -->
        <div class="mt-6 rounded-2xl border border-slate-700/50 bg-slate-900/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-slate-400">О себе</h3>
          <div v-if="!isEditing">
            <p class="leading-relaxed text-slate-300">{{ userData.bio || 'Информация не заполнена' }}</p>
          </div>
          <div v-else>
            <textarea
              v-model="editData.bio"
              rows="4"
              class="w-full rounded-lg border border-slate-600 bg-slate-800 p-3 text-slate-100 focus:border-indigo-500 focus:outline-none"
              placeholder="Расскажите о себе..."
            ></textarea>
          </div>
        </div>
        <div v-if="isEditing" class="mt-4 flex gap-3">
          <button class="rounded-lg bg-green-600 px-6 py-2 font-semibold text-white transition-colors hover:bg-green-500 disabled:opacity-60" :disabled="saving" @click="saveProfile">
            {{ saving ? 'Сохраняем...' : 'Сохранить' }}
          </button>
          <button class="rounded-lg bg-gray-600 px-6 py-2 font-semibold text-white transition-colors hover:bg-gray-500" @click="cancelEditing">
            Отмена
          </button>
        </div>
      </div>
    </section>

    <!-- НОВАЯ СЕКЦИЯ ГРАФИКА АКТИВНОСТИ (как в публичном профиле) -->
  <section
  v-if="showActivityHeatmap"
  class="rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-8 shadow-xl backdrop-blur-md"
>
  <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
    <div>
      <h2 class="text-2xl font-bold text-slate-100">{{ activityTitle }}</h2>
      <p class="mt-2 text-sm text-slate-400">
        {{ activityDescription }}
      </p>
    </div>

    <div class="rounded-2xl border border-slate-700 bg-slate-900/50 px-4 py-3 text-right">
      <p class="text-xs uppercase tracking-[0.25em] text-slate-500">Активностей за год</p>
      <p class="mt-2 text-2xl font-black text-white">{{ totalActivityCount }}</p>
    </div>
  </div>

  <div class="mt-6 grid gap-6 xl:grid-cols-[1fr,92px]">
    <!-- Основная сетка -->
    <div class="rounded-3xl border border-slate-700/50 bg-slate-900/50 p-4">
      <div class="overflow-x-auto pb-2">
        <div class="inline-flex min-w-max gap-3">
          <div class="pt-7 text-[10px] text-slate-500">
            <div
              v-for="(label, index) in WEEKDAY_LABELS"
              :key="index"
              class="flex h-4 items-center"
            >
              {{ label }}
            </div>
          </div>

          <div>
            <div class="mb-2 flex gap-1 text-[10px] uppercase tracking-[0.2em] text-slate-500">
              <div
                v-for="(week, index) in heatmap.weeks"
                :key="`month-${index}`"
                class="w-4"
              >
                {{ heatmap.monthLabels[index] || '' }}
              </div>
            </div>

            <div class="flex gap-1">
              <div
                v-for="(week, weekIndex) in heatmap.weeks"
                :key="`week-${weekIndex}`"
                class="flex flex-col gap-1"
              >
                <div
                  v-for="day in week"
                  :key="day.date"
                  class="h-4 w-4 rounded-[4px] transition-transform hover:scale-125"
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

    <!-- Блок выбора года (справа, как в публичном профиле) -->
    <div class="rounded-3xl border border-slate-700/50 bg-slate-900/50 p-3">
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

    <!-- Секция навыков (без изменений) -->
    <section
      v-if="userData.role === 'student'"
      class="rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-8 shadow-xl backdrop-blur-md"
    >
      <h2 class="border-b border-slate-700 pb-4 text-2xl font-bold text-slate-100">
        Цифровой паспорт навыков
      </h2>
      <div class="mt-8 grid gap-6 xl:grid-cols-2">
        <div class="rounded-3xl border border-slate-700/50 bg-slate-900/50 p-6">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h3 class="text-lg font-bold text-white">В процессе изучения</h3>
              <p class="mt-1 text-sm text-slate-400">Навыки, которые открываются по мере прохождения уроков.</p>
            </div>
            <span class="rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-300">
              {{ learningSkills.length }}
            </span>
          </div>
          <div v-if="learningSkills.length" class="mt-6 space-y-4">
            <div v-for="skill in learningSkills" :key="`${skill.course_name}-${skill.id}`" class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <div class="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p class="font-bold text-slate-100">{{ skill.name }}</p>
                  <p class="mt-1 text-sm text-slate-500">{{ skill.course_name }}</p>
                </div>
                <span class="text-sm font-bold text-emerald-300">{{ skill.progress_percentage }}%</span>
              </div>
              <div class="h-3 overflow-hidden rounded-full bg-slate-800">
                <div class="h-full rounded-full bg-gradient-to-r from-indigo-600 to-emerald-500 transition-all duration-500" :style="{ width: `${skill.progress_percentage}%` }"></div>
              </div>
            </div>
          </div>
          <div v-else class="mt-6 rounded-2xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
            Вы пока не начали курс, который открыл бы новые навыки в процессе изучения.
          </div>
        </div>
        <div class="rounded-3xl border border-slate-700/50 bg-slate-900/50 p-6">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h3 class="text-lg font-bold text-white">Подтвержденные</h3>
              <p class="mt-1 text-sm text-slate-400">Навыки, уже закрепленные успешной сдачей Quiz.</p>
            </div>
            <span class="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-300">
              {{ completedSkills.length }}
            </span>
          </div>
          <div v-if="completedSkills.length" class="mt-6 flex flex-wrap gap-3">
            <span v-for="skill in completedSkills" :key="skill.id" class="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
              <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
              </svg>
              {{ skill.name }}
            </span>
          </div>
          <div v-else class="mt-6 rounded-2xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
            Подтвержденных навыков пока нет. Завершайте уроки и проходите Quiz, чтобы заполнять цифровой паспорт.
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
