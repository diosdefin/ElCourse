<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import api from '../api'
import { resolveMediaUrl } from '../utils/media'
import { showError } from '../utils/toast'

const analytics = ref(null)
const loading = ref(true)
const pageError = ref('')
const activeTab = ref('overview')
const searchQuery = ref('')
const progressFilter = ref('all')
const coursePage = ref(1)
const studentPage = ref(1)
const coursesPerPage = ref(4)
const studentsPerPage = ref(8)
const brokenAvatars = ref(new Set())

const tabs = [
  { id: 'overview', label: 'Обзор' },
  { id: 'courses', label: 'Курсы' },
  { id: 'students', label: 'Студенты' },
]

const coursePageSizes = [4, 8, 12]
const studentPageSizes = [8, 12, 20]

const summary = computed(() => analytics.value?.summary || {})
const courses = computed(() => Array.isArray(analytics.value?.courses) ? analytics.value.courses : [])
const students = computed(() => Array.isArray(analytics.value?.students) ? analytics.value.students : [])
const activity = computed(() => Array.isArray(analytics.value?.activity) ? analytics.value.activity : [])

const lessonTypeCounts = computed(() => summary.value.lesson_type_counts || {})
const normalizedQuery = computed(() => searchQuery.value.trim().toLowerCase())

const filteredCourses = computed(() => {
  const query = normalizedQuery.value
  if (!query) return courses.value

  return courses.value.filter((course) => {
    const haystack = [
      course.title,
      course.description,
      ...(course.skills || []).map((skill) => skill.name),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()

    return haystack.includes(query)
  })
})

const filteredStudents = computed(() => {
  const query = normalizedQuery.value
  return students.value.filter((row) => {
    const matchesQuery = !query || [row.username, row.email, row.course_title]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(query)

    if (!matchesQuery) return false

    const progress = Number(row.progress_percentage) || 0
    if (progressFilter.value === 'completed') return progress >= 100
    if (progressFilter.value === 'risk') return progress > 0 && progress < 50
    if (progressFilter.value === 'active') return progress >= 50 && progress < 100
    return true
  })
})

const topCourses = computed(() => {
  return [...courses.value]
    .sort((a, b) => (b.student_count || 0) - (a.student_count || 0))
    .slice(0, 5)
})

const recentStudents = computed(() => {
  return [...students.value]
    .sort((a, b) => new Date(b.last_activity || 0).getTime() - new Date(a.last_activity || 0).getTime())
    .slice(0, 6)
})

const maxActivity = computed(() => Math.max(...activity.value.map((item) => Number(item.count) || 0), 1))

const totalCoursePages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / coursesPerPage.value)))
const totalStudentPages = computed(() => Math.max(1, Math.ceil(filteredStudents.value.length / studentsPerPage.value)))

const paginatedCourses = computed(() => {
  const start = (coursePage.value - 1) * coursesPerPage.value
  return filteredCourses.value.slice(start, start + coursesPerPage.value)
})

const paginatedStudents = computed(() => {
  const start = (studentPage.value - 1) * studentsPerPage.value
  return filteredStudents.value.slice(start, start + studentsPerPage.value)
})

const courseRangeLabel = computed(() => buildRangeLabel(filteredCourses.value.length, coursePage.value, coursesPerPage.value))
const studentRangeLabel = computed(() => buildRangeLabel(filteredStudents.value.length, studentPage.value, studentsPerPage.value))

watch([searchQuery, progressFilter], () => {
  coursePage.value = 1
  studentPage.value = 1
})

watch([coursesPerPage, studentsPerPage], () => {
  coursePage.value = 1
  studentPage.value = 1
})

watch(totalCoursePages, (pages) => {
  if (coursePage.value > pages) coursePage.value = pages
})

watch(totalStudentPages, (pages) => {
  if (studentPage.value > pages) studentPage.value = pages
})

const fetchAnalytics = async () => {
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/teacher/analytics/')
    analytics.value = response.data
    coursePage.value = 1
    studentPage.value = 1
    brokenAvatars.value = new Set()
  } catch (error) {
    console.error('Ошибка загрузки аналитики:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить аналитику преподавателя.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const buildRangeLabel = (total, page, perPage) => {
  if (!total) return '0 из 0'
  const start = (page - 1) * perPage + 1
  const end = Math.min(page * perPage, total)
  return `${start}–${end} из ${total}`
}

const formatNumber = (value) => {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

const formatDate = (value) => {
  if (!value) return 'нет данных'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'нет данных'
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

const formatPercent = (value) => `${formatNumber(value)}%`

const progressTone = (value) => {
  const progress = Number(value) || 0
  if (progress >= 80) return 'bg-emerald-400'
  if (progress >= 50) return 'bg-sky-400'
  if (progress > 0) return 'bg-amber-400'
  return 'bg-slate-600'
}

const avatarKey = (row) => `${row.student_id || row.id || row.username || 'student'}-${row.course_id || 'global'}`

const getMediaUrl = (url) => {
  return resolveMediaUrl(url)
}

const shouldShowAvatar = (row) => Boolean(row?.avatar && !brokenAvatars.value.has(avatarKey(row)))

const markAvatarBroken = (row) => {
  const next = new Set(brokenAvatars.value)
  next.add(avatarKey(row))
  brokenAvatars.value = next
}

const roleInitial = (name) => {
  const prepared = String(name || 'S')
    .replace(/[_-]+/g, ' ')
    .trim()
  const parts = prepared.split(/\s+/).filter(Boolean)
  if (parts.length > 1) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return prepared.charAt(0).toUpperCase() || 'S'
}

const goToCoursePage = (page) => {
  coursePage.value = Math.min(Math.max(1, page), totalCoursePages.value)
}

const goToStudentPage = (page) => {
  studentPage.value = Math.min(Math.max(1, page), totalStudentPages.value)
}

onMounted(fetchAnalytics)
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
    <header class="mb-6 overflow-hidden rounded-3xl border border-slate-700/60 bg-slate-900/65 shadow-xl shadow-slate-950/10 backdrop-blur">
      <div class="relative p-5 sm:p-7">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/60 to-transparent"></div>
        <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl">
            <div class="mb-3 inline-flex items-center rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] text-sky-200">
              Аналитика преподавателя
            </div>
            <h1 class="text-2xl font-black tracking-tight text-slate-50 sm:text-3xl">Мониторинг курсов и студентов</h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Сводка по структуре курсов, активности, прогрессу студентов и результатам тестовых уроков. Раздел помогает быстро понять, какие курсы требуют внимания.
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <RouterLink
              :to="{ name: 'teacher-dashboard' }"
              class="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm font-bold text-slate-200 transition hover:border-sky-400/60 hover:text-white"
            >
              К курсам
            </RouterLink>
            <button
              class="inline-flex items-center justify-center rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-black text-white shadow-lg shadow-sky-600/20 transition hover:bg-sky-500 active:scale-[0.98]"
              type="button"
              @click="fetchAnalytics"
            >
              Обновить
            </button>
          </div>
        </div>
      </div>
    </header>

    <div v-if="loading" class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <div v-for="index in 8" :key="index" class="h-24 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/60"></div>
    </div>

    <section v-else-if="pageError" class="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-8 text-center">
      <h2 class="text-xl font-black text-rose-100">Не удалось открыть аналитику</h2>
      <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-rose-100/80">{{ pageError }}</p>
      <button class="mt-6 rounded-xl bg-rose-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-rose-400" type="button" @click="fetchAnalytics">
        Повторить
      </button>
    </section>

    <div v-else>
      <section class="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article class="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-4">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Курсы</p>
          <strong class="mt-2 block text-2xl font-black text-slate-50">{{ formatNumber(summary.total_courses) }}</strong>
          <p class="mt-1 text-xs text-slate-500">Всего программ автора</p>
        </article>

        <article class="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-4">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Студенты</p>
          <strong class="mt-2 block text-2xl font-black text-emerald-300">{{ formatNumber(summary.students_count) }}</strong>
          <p class="mt-1 text-xs text-slate-500">Есть активность в курсах</p>
        </article>

        <article class="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-4">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Уроки</p>
          <strong class="mt-2 block text-2xl font-black text-slate-50">{{ formatNumber(summary.total_lessons) }}</strong>
          <p class="mt-1 text-xs text-slate-500">Опубликовано: {{ formatNumber(summary.published_lessons) }}</p>
        </article>

        <article class="rounded-2xl border border-slate-700/60 bg-slate-900/50 p-4">
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Средний балл</p>
          <strong class="mt-2 block text-2xl font-black text-sky-300">{{ formatPercent(summary.average_score) }}</strong>
          <p class="mt-1 text-xs text-slate-500">По тестам с результатом</p>
        </article>
      </section>

      <nav class="mb-5 flex flex-wrap gap-1.5 rounded-2xl border border-slate-700/60 bg-slate-900/45 p-1.5">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="rounded-xl px-4 py-2 text-sm font-black transition"
          :class="activeTab === tab.id ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'"
          type="button"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </nav>

      <section v-if="activeTab === 'overview'" class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div class="grid gap-5">
          <article class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
            <div class="mb-4">
              <h2 class="text-lg font-black text-slate-50">Структура учебного контента</h2>
              <p class="mt-1 text-sm text-slate-500">Распределение уроков по типам.</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div class="rounded-2xl border border-slate-800 bg-slate-950/25 p-4">
                <span class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Текстовые</span>
                <strong class="mt-2 block text-2xl font-black text-slate-100">{{ formatNumber(lessonTypeCounts.text) }}</strong>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/25 p-4">
                <span class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Видео</span>
                <strong class="mt-2 block text-2xl font-black text-indigo-300">{{ formatNumber(lessonTypeCounts.video) }}</strong>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/25 p-4">
                <span class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Тесты</span>
                <strong class="mt-2 block text-2xl font-black text-violet-300">{{ formatNumber(lessonTypeCounts.quiz) }}</strong>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/25 p-4">
                <span class="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Экзамены</span>
                <strong class="mt-2 block text-2xl font-black text-amber-300">{{ formatNumber(lessonTypeCounts.final_exam) }}</strong>
              </div>
            </div>
          </article>

          <article class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
            <h2 class="text-lg font-black text-slate-50">Самые активные курсы</h2>
            <p class="mt-1 text-sm text-slate-500">Курсы отсортированы по количеству студентов с прогрессом.</p>

            <div v-if="topCourses.length" class="mt-4 grid gap-3">
              <div v-for="course in topCourses" :key="course.id" class="rounded-2xl border border-slate-800 bg-slate-950/20 p-4">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 class="font-black text-slate-100">{{ course.title }}</h3>
                    <p class="mt-1 text-xs text-slate-500">{{ course.student_count }} студентов · {{ course.lesson_count }} уроков</p>
                  </div>
                  <strong class="text-sm font-black text-sky-300">{{ formatPercent(course.average_progress) }}</strong>
                </div>
                <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
                  <div class="h-full rounded-full" :class="progressTone(course.average_progress)" :style="{ width: `${Math.min(course.average_progress || 0, 100)}%` }"></div>
                </div>
              </div>
            </div>

            <div v-else class="mt-4 rounded-2xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
              Пока нет данных о прохождении курсов.
            </div>
          </article>
        </div>

        <aside class="grid gap-5">
          <article class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
            <h2 class="text-lg font-black text-slate-50">Активность автора</h2>
            <p class="mt-1 text-sm text-slate-500">Создание курсов, уроков, загрузка видео и обновление тестов.</p>

            <div v-if="activity.length" class="mt-4 flex h-32 items-end gap-1 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/25 p-3">
              <div
                v-for="item in activity.slice(-60)"
                :key="item.date"
                class="min-w-1 flex-1 rounded-t bg-sky-400/70"
                :title="`${item.date}: ${item.count}`"
                :style="{ height: `${Math.max(8, (Number(item.count) / maxActivity) * 100)}%` }"
              ></div>
            </div>
            <div v-else class="mt-4 rounded-2xl border border-dashed border-slate-700 p-5 text-center text-sm text-slate-500">
              Активность пока не зафиксирована.
            </div>
          </article>

          <article class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
            <h2 class="text-lg font-black text-slate-50">Последняя активность студентов</h2>
            <div v-if="recentStudents.length" class="mt-4 grid gap-2.5">
              <div v-for="row in recentStudents" :key="`${row.course_id}-${row.student_id}`" class="rounded-2xl border border-slate-800 bg-slate-950/20 p-3">
                <div class="flex items-center gap-3">
                  <div class="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-sky-500/20 to-violet-500/20">
                    <img
                      v-if="shouldShowAvatar(row)"
                      :src="getMediaUrl(row.avatar)"
                      :alt="row.username"
                      class="h-full w-full object-cover"
                      loading="lazy"
                      @error="markAvatarBroken(row)"
                    >
                    <span v-else class="text-xs font-black text-sky-100">{{ roleInitial(row.username) }}</span>
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-black text-slate-100">{{ row.username }}</p>
                    <p class="truncate text-xs text-slate-500">{{ row.course_title }}</p>
                  </div>
                </div>
                <p class="mt-2 text-xs text-slate-500">Последнее действие: {{ formatDate(row.last_activity) }}</p>
              </div>
            </div>
            <div v-else class="mt-4 rounded-2xl border border-dashed border-slate-700 p-5 text-center text-sm text-slate-500">
              Данных по студентам пока нет.
            </div>
          </article>
        </aside>
      </section>

      <section v-else-if="activeTab === 'courses'" class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
        <div class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 class="text-lg font-black text-slate-50">Аналитика по курсам</h2>
            <p class="mt-1 text-sm text-slate-500">Структура, охват студентов и средний прогресс.</p>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              v-model="searchQuery"
              class="w-full rounded-xl border border-slate-700 bg-slate-950/45 px-4 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-sky-400 lg:w-80"
              type="search"
              placeholder="Поиск по курсам и навыкам"
            >
            <select v-model.number="coursesPerPage" class="rounded-xl border border-slate-700 bg-slate-950/45 px-3 py-2.5 text-sm font-bold text-slate-200 outline-none focus:border-sky-400">
              <option v-for="size in coursePageSizes" :key="size" :value="size">{{ size }} на странице</option>
            </select>
          </div>
        </div>

        <div v-if="paginatedCourses.length" class="grid gap-3">
          <article v-for="course in paginatedCourses" :key="course.id" class="rounded-2xl border border-slate-800 bg-slate-950/25 p-4">
            <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
              <div class="min-w-0">
                <h3 class="text-lg font-black text-slate-50">{{ course.title }}</h3>
                <div class="mt-2 flex flex-wrap gap-1.5">
                  <span v-for="skill in course.skills" :key="skill.id" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-[11px] font-bold text-sky-200">
                    {{ skill.name }}
                  </span>
                  <span v-if="!course.skills?.length" class="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-bold text-slate-500">
                    Навыки не указаны
                  </span>
                </div>
              </div>

              <div class="flex flex-wrap gap-2">
                <RouterLink :to="{ name: 'teacher-lesson-editor', params: { id: course.id } }" class="rounded-xl bg-indigo-600 px-3 py-2 text-xs font-black text-white transition hover:bg-indigo-500">
                  Конструктор
                </RouterLink>
                <RouterLink :to="{ name: 'quiz-editor', params: { id: course.id } }" class="rounded-xl border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-xs font-bold text-violet-200 transition hover:bg-violet-500 hover:text-white">
                  Тесты
                </RouterLink>
                <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }" class="rounded-xl border border-slate-700 bg-slate-800/70 px-3 py-2 text-xs font-bold text-slate-200 transition hover:border-sky-400/60 hover:text-white">
                  Просмотр
                </RouterLink>
              </div>
            </div>

            <div class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Модули</p>
                <strong class="text-xl font-black text-slate-100">{{ course.module_count }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Уроки</p>
                <strong class="text-xl font-black text-slate-100">{{ course.lesson_count }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Опубликовано</p>
                <strong class="text-xl font-black text-emerald-300">{{ course.published_lesson_count }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Студенты</p>
                <strong class="text-xl font-black text-sky-300">{{ course.student_count }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Прогресс</p>
                <strong class="text-xl font-black text-slate-100">{{ formatPercent(course.average_progress) }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
                <p class="text-[11px] text-slate-500">Средний балл</p>
                <strong class="text-xl font-black text-violet-300">{{ formatPercent(course.average_score) }}</strong>
              </div>
            </div>
          </article>
        </div>

        <div v-else class="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">
          Курсы по выбранному запросу не найдены.
        </div>

        <footer v-if="filteredCourses.length" class="mt-4 flex flex-col gap-3 border-t border-slate-800/80 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <span class="text-sm font-bold text-slate-500">Показано: {{ courseRangeLabel }}</span>
          <div class="flex items-center gap-2">
            <button class="rounded-xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-300 transition hover:border-sky-400 disabled:cursor-not-allowed disabled:opacity-40" type="button" :disabled="coursePage <= 1" @click="goToCoursePage(coursePage - 1)">
              Назад
            </button>
            <span class="rounded-xl bg-slate-950/50 px-3 py-2 text-sm font-black text-slate-200">{{ coursePage }} / {{ totalCoursePages }}</span>
            <button class="rounded-xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-300 transition hover:border-sky-400 disabled:cursor-not-allowed disabled:opacity-40" type="button" :disabled="coursePage >= totalCoursePages" @click="goToCoursePage(coursePage + 1)">
              Далее
            </button>
          </div>
        </footer>
      </section>

      <section v-else class="rounded-3xl border border-slate-700/60 bg-slate-900/50 p-5">
        <div class="mb-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 class="text-lg font-black text-slate-50">Мониторинг студентов</h2>
            <p class="mt-1 text-sm text-slate-500">Прогресс студентов по курсам преподавателя.</p>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row">
            <input
              v-model="searchQuery"
              class="w-full rounded-xl border border-slate-700 bg-slate-950/45 px-4 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-sky-400 sm:w-72"
              type="search"
              placeholder="Студент или курс"
            >
            <select v-model="progressFilter" class="rounded-xl border border-slate-700 bg-slate-950/45 px-3 py-2.5 text-sm font-bold text-slate-200 outline-none transition focus:border-sky-400">
              <option value="all">Все</option>
              <option value="active">В процессе</option>
              <option value="risk">Низкий прогресс</option>
              <option value="completed">Завершили</option>
            </select>
            <select v-model.number="studentsPerPage" class="rounded-xl border border-slate-700 bg-slate-950/45 px-3 py-2.5 text-sm font-bold text-slate-200 outline-none focus:border-sky-400">
              <option v-for="size in studentPageSizes" :key="size" :value="size">{{ size }} на странице</option>
            </select>
          </div>
        </div>

        <div v-if="paginatedStudents.length" class="overflow-hidden rounded-2xl border border-slate-800">
          <div class="hidden grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_120px_120px_140px] gap-4 border-b border-slate-800 bg-slate-950/55 px-4 py-3 text-[11px] font-black uppercase tracking-[0.14em] text-slate-500 xl:grid">
            <span>Студент</span>
            <span>Курс</span>
            <span>Прогресс</span>
            <span>Баллы</span>
            <span>Активность</span>
          </div>

          <div class="divide-y divide-slate-800">
            <article v-for="row in paginatedStudents" :key="`${row.course_id}-${row.student_id}`" class="grid gap-4 p-4 transition hover:bg-slate-950/20 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1.4fr)_120px_120px_140px] xl:items-center">
              <div class="flex min-w-0 items-center gap-3">
                <div class="relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-700 bg-gradient-to-br from-sky-500/20 via-slate-800 to-violet-500/20 shadow-inner shadow-slate-950/40">
                  <img
                    v-if="shouldShowAvatar(row)"
                    :src="getMediaUrl(row.avatar)"
                    :alt="row.username"
                    class="h-full w-full object-cover"
                    loading="lazy"
                    @error="markAvatarBroken(row)"
                  >
                  <span v-else class="text-sm font-black text-sky-100">{{ roleInitial(row.username) }}</span>
                </div>
                <div class="min-w-0">
                  <p class="truncate font-black text-slate-100">{{ row.username }}</p>
                  <p class="truncate text-xs text-slate-500">{{ row.email || 'email не указан' }}</p>
                </div>
              </div>

              <div class="min-w-0">
                <p class="truncate text-sm font-bold text-slate-200">{{ row.course_title }}</p>
                <p class="mt-1 text-xs text-slate-500">{{ row.completed_lessons }} из {{ row.total_lessons }} уроков</p>
              </div>

              <div>
                <strong class="text-sm font-black text-slate-100">{{ formatPercent(row.progress_percentage) }}</strong>
                <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                  <div class="h-full rounded-full" :class="progressTone(row.progress_percentage)" :style="{ width: `${Math.min(row.progress_percentage || 0, 100)}%` }"></div>
                </div>
              </div>

              <div class="text-sm font-black text-violet-300">{{ row.average_score ? formatPercent(row.average_score) : '—' }}</div>
              <div class="text-xs font-bold text-slate-500">{{ formatDate(row.last_activity) }}</div>
            </article>
          </div>
        </div>

        <div v-else class="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">
          Данных по студентам пока нет или фильтр ничего не нашёл.
        </div>

        <footer v-if="filteredStudents.length" class="mt-4 flex flex-col gap-3 border-t border-slate-800/80 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <span class="text-sm font-bold text-slate-500">Показано: {{ studentRangeLabel }}</span>
          <div class="flex items-center gap-2">
            <button class="rounded-xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-300 transition hover:border-sky-400 disabled:cursor-not-allowed disabled:opacity-40" type="button" :disabled="studentPage <= 1" @click="goToStudentPage(studentPage - 1)">
              Назад
            </button>
            <span class="rounded-xl bg-slate-950/50 px-3 py-2 text-sm font-black text-slate-200">{{ studentPage }} / {{ totalStudentPages }}</span>
            <button class="rounded-xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-300 transition hover:border-sky-400 disabled:cursor-not-allowed disabled:opacity-40" type="button" :disabled="studentPage >= totalStudentPages" @click="goToStudentPage(studentPage + 1)">
              Далее
            </button>
          </div>
        </footer>
      </section>
    </div>
  </div>
</template>
