<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { showError } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const course = ref(null)
const loading = ref(true)
const hasLessonFlow = ref(false)

const userRole = computed(() => localStorage.getItem('user_role') || '')
const canEditCourse = computed(() => ['teacher', 'admin'].includes(userRole.value))
const lessons = computed(() => course.value?.lessons || [])
const lessonCount = computed(() => lessons.value.length)
const completedCount = computed(() => lessons.value.filter((lesson) => lesson.is_completed).length)
const progressPercentage = computed(() => Number(course.value?.progress_percentage || 0))

const primaryActionLabel = computed(() => {
  if (!hasLessonFlow.value) return 'Материалы пока недоступны'
  if (progressPercentage.value >= 100) return 'Открыть курс'
  if (progressPercentage.value > 0 || completedCount.value > 0) return 'Продолжить обучение'
  return 'Начать обучение'
})

const loadCourse = async () => {
  loading.value = true
  try {
    const response = await api.get(`/courses/${route.params.id}/`)
    course.value = response.data
    hasLessonFlow.value = Array.isArray(response.data?.lessons) && response.data.lessons.length > 0
  } catch (error) {
    console.error('Не удалось загрузить курс', error)
    showError('Не удалось загрузить страницу курса.')
  } finally {
    loading.value = false
  }
}

onMounted(loadCourse)
</script>

<template>
  <div v-if="loading" class="mx-auto flex h-[65vh] max-w-6xl items-center justify-center px-4">
    <div class="rounded-3xl border border-slate-800 bg-slate-900/70 px-8 py-7 text-center shadow-2xl shadow-slate-950/20">
      <div class="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-400"></div>
      <p class="mt-4 text-sm font-medium text-slate-400">Загружаем информацию о курсе...</p>
    </div>
  </div>

  <div v-else-if="course" class="mx-auto mt-4 max-w-6xl px-0 pb-12 sm:mt-8 sm:px-4">
    <button
      class="btn-secondary mb-5 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold"
      @click="router.back()"
    >
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      Назад
    </button>

    <section class="card-glass overflow-hidden rounded-[2rem]">
      <div class="grid lg:grid-cols-[minmax(0,1fr),360px]">
        <div class="min-w-0 p-5 sm:p-8 lg:p-10">
          <div class="mb-5 flex flex-wrap items-center gap-2">
            <span class="rounded-full border border-indigo-400/25 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.22em] text-indigo-200">
              Учебный курс
            </span>
            <span class="rounded-full border border-slate-700 bg-slate-950/45 px-3 py-1 text-xs font-bold text-slate-400">
              {{ lessonCount }} урок.
            </span>
          </div>

          <h1 class="max-w-4xl break-words text-2xl font-black leading-tight text-slate-100 sm:text-5xl">
            {{ course.title }}
          </h1>

          <p class="mt-4 text-sm font-semibold text-slate-400">
            Автор курса: <span class="text-slate-200">{{ course.author_name || 'Не указан' }}</span>
          </p>

          <p class="mt-6 max-w-3xl whitespace-pre-line break-words text-sm leading-7 text-slate-300 sm:text-base sm:leading-8">
            {{ course.description || 'Описание курса пока не добавлено.' }}
          </p>

          <div v-if="course.skills_covered?.length" class="mt-7">
            <p class="mb-3 text-xs font-bold uppercase tracking-[0.22em] text-slate-500">Навыки после прохождения</p>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="skill in course.skills_covered"
                :key="skill.id || skill.name"
                class="rounded-xl border border-indigo-400/20 bg-indigo-500/10 px-3 py-2 text-sm font-bold text-indigo-100"
              >
                {{ skill.name || skill }}
              </span>
            </div>
          </div>

          <div class="mt-8 grid gap-3 sm:flex sm:flex-wrap sm:items-center">
            <RouterLink
              v-if="hasLessonFlow"
              :to="{ name: 'course-play', params: { id: course.id } }"
              class="btn-primary inline-flex items-center justify-center gap-2 px-7 text-center text-sm font-black"
            >
              {{ primaryActionLabel }}
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </RouterLink>

            <div
              v-else
              class="inline-flex cursor-not-allowed items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/50 px-7 py-3 text-center text-sm font-bold text-slate-500"
            >
              {{ primaryActionLabel }}
            </div>

            <RouterLink
              v-if="canEditCourse"
              :to="{ name: 'teacher-lesson-editor', params: { id: course.id } }"
              class="btn-glass inline-flex items-center justify-center px-7 text-center text-sm font-black text-emerald-100"
            >
              Открыть конструктор
            </RouterLink>
          </div>
        </div>

        <aside class="min-w-0 border-t border-slate-800 bg-slate-950/35 p-5 sm:p-8 lg:border-l lg:border-t-0">
          <div class="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900">
            <img v-if="course.image" :src="course.image" :alt="course.title" class="h-52 w-full object-cover">
            <div v-else class="flex h-52 w-full items-center justify-center bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 text-slate-500">
              <svg class="h-16 w-16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 6.5A2.5 2.5 0 016.5 4h11A2.5 2.5 0 0120 6.5v11a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 014 17.5v-11z" stroke="currentColor" stroke-width="1.5" />
                <path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
              </svg>
            </div>
          </div>

          <div class="mt-5 space-y-3">
            <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <div class="mb-3 flex items-center justify-between text-sm">
                <span class="font-bold text-slate-200">Прогресс курса</span>
                <span class="font-black text-indigo-300">{{ progressPercentage }}%</span>
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-slate-950">
                <div class="h-full rounded-full bg-indigo-500 transition-all duration-500" :style="{ width: `${progressPercentage}%` }"></div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Уроки</p>
                <p class="mt-1 text-2xl font-black text-slate-100">{{ lessonCount }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Пройдено</p>
                <p class="mt-1 text-2xl font-black text-emerald-300">{{ completedCount }}</p>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section class="mt-6 grid gap-4 md:grid-cols-3">
      <div class="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
        <div class="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 text-indigo-200">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 4h14v16H5V4z" stroke="currentColor" stroke-width="1.6" />
            <path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </div>
        <h3 class="text-lg font-black text-slate-100">Структурное обучение</h3>
        <p class="mt-2 text-sm leading-6 text-slate-500">Курс проходит через модули, уроки, тесты и финальную проверку знаний.</p>
      </div>

      <div class="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
        <div class="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-500/10 text-emerald-200">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 3l7 4v5c0 4.2-2.9 7.2-7 9-4.1-1.8-7-4.8-7-9V7l7-4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M9 12l2 2 4-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h3 class="text-lg font-black text-slate-100">Подтверждение навыков</h3>
        <p class="mt-2 text-sm leading-6 text-slate-500">Результаты тестов и прогресс используются как часть цифрового профиля студента.</p>
      </div>

      <div class="rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
        <div class="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-600/40 bg-slate-800/60 text-slate-300">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M4 7h16M7 7V5h10v2M6 7l1 13h10l1-13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h3 class="text-lg font-black text-slate-100">Единый маршрут</h3>
        <p class="mt-2 text-sm leading-6 text-slate-500">Описание курса остаётся отдельной страницей, а обучение открывается одной понятной кнопкой.</p>
      </div>
    </section>

    <section v-if="!hasLessonFlow && course.progress_percentage === 100" class="mt-6 rounded-3xl border border-indigo-400/20 bg-indigo-500/10 p-6 text-center">
      <h3 class="text-xl font-black text-slate-100">Доступен старый формат тестирования</h3>
      <p class="mx-auto mt-2 max-w-2xl text-sm text-slate-400">Этот курс создан до новой модульной структуры. Итоговый тест можно открыть отдельно.</p>
      <RouterLink
        :to="{ name: 'course-quiz', params: { id: course.id } }"
        class="mt-5 inline-flex w-full justify-center rounded-2xl bg-indigo-600 px-7 py-3 text-center text-sm font-black text-white transition hover:bg-indigo-500 sm:w-auto"
      >
        Открыть итоговый тест
      </RouterLink>
    </section>
  </div>
</template>
