<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import LessonView from './LessonView.vue'
import { showError } from '../utils/toast'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const outline = ref(null)
const selectedLessonId = ref(null)
const expandedModules = ref({})

const courseId = computed(() => Number(route.params.id))
const modules = computed(() => outline.value?.modules || [])

const allLessons = computed(() => modules.value.flatMap((moduleItem) => moduleItem.lessons || []))
const totalLessons = computed(() => allLessons.value.length)
const completedLessons = computed(() => allLessons.value.filter((lesson) => lesson.is_completed).length)
const availableLessons = computed(() => allLessons.value.filter((lesson) => !lesson.is_locked).length)
const progressPercent = computed(() => {
  if (!totalLessons.value) return 0
  return Math.round((completedLessons.value / totalLessons.value) * 100)
})

const selectedLesson = computed(() => allLessons.value.find((lesson) => lesson.id === selectedLessonId.value) || null)
const activeModuleId = computed(() => {
  const moduleItem = modules.value.find((item) =>
    (item.lessons || []).some((lesson) => lesson.id === selectedLessonId.value)
  )
  return moduleItem?.id || null
})
const activeModuleIndex = computed(() => modules.value.findIndex((item) => item.id === activeModuleId.value))

const lessonTypeLabel = (lessonType) => {
  if (lessonType === 'video') return 'Видео'
  if (lessonType === 'text') return 'Текст'
  if (lessonType === 'quiz') return 'Тест'
  if (lessonType === 'final_exam') return 'Экзамен'
  return 'Урок'
}

const lessonStatusLabel = (lesson) => {
  if (lesson.is_completed) return 'Пройден'
  if (lesson.is_locked) return 'Закрыт'
  return 'Доступен'
}

const lessonStatusClass = (lesson) => {
  if (lesson.is_completed) return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
  if (lesson.is_locked) return 'border-slate-700/70 bg-slate-950/50 text-slate-500'
  return 'border-slate-700/70 bg-slate-950/40 text-slate-300'
}

const moduleProgress = (moduleItem) => {
  const lessons = moduleItem.lessons || []
  if (!lessons.length) return 0
  const completed = lessons.filter((lesson) => lesson.is_completed).length
  return Math.round((completed / lessons.length) * 100)
}

const findDefaultLessonId = () => {
  const firstIncomplete = allLessons.value.find((lesson) => !lesson.is_locked && !lesson.is_completed)
  if (firstIncomplete) return firstIncomplete.id

  const firstUnlocked = allLessons.value.find((lesson) => !lesson.is_locked)
  if (firstUnlocked) return firstUnlocked.id

  return allLessons.value[0]?.id || null
}

const expandAroundSelectedLesson = () => {
  const expanded = {}

  for (const moduleItem of modules.value) {
    const hasSelectedLesson = (moduleItem.lessons || []).some((lesson) => lesson.id === selectedLessonId.value)
    const hasAvailableLesson = (moduleItem.lessons || []).some((lesson) => !lesson.is_locked)
    expanded[moduleItem.id] = hasSelectedLesson || hasAvailableLesson
  }

  expandedModules.value = expanded
}

const fetchOutline = async () => {
  loading.value = true
  try {
    const response = await api.get(`/courses/${courseId.value}/outline/`)
    outline.value = response.data

    if (!selectedLessonId.value) {
      selectedLessonId.value = findDefaultLessonId()
    } else {
      const stillExists = allLessons.value.some((lesson) => lesson.id === selectedLessonId.value)
      const stillAccessible = allLessons.value.some((lesson) => lesson.id === selectedLessonId.value && !lesson.is_locked)
      if (!stillExists || !stillAccessible) {
        selectedLessonId.value = findDefaultLessonId()
      }
    }

    expandAroundSelectedLesson()
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить структуру курса.')
  } finally {
    loading.value = false
  }
}

const selectLesson = (lesson, moduleId) => {
  if (lesson.is_locked) {
    showError('Этот урок пока закрыт. Завершите предыдущие уроки курса.')
    return
  }

  selectedLessonId.value = lesson.id
  expandedModules.value = {
    ...expandedModules.value,
    [moduleId]: true,
  }
}

const toggleModule = (moduleId) => {
  expandedModules.value = {
    ...expandedModules.value,
    [moduleId]: !expandedModules.value[moduleId],
  }
}

onMounted(fetchOutline)
</script>

<template>
  <div v-if="loading" class="mx-auto flex h-[65vh] max-w-6xl items-center justify-center px-4">
    <div class="rounded-3xl border border-slate-800 bg-slate-900/70 px-8 py-7 text-center shadow-2xl shadow-slate-950/20">
      <div class="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-400"></div>
      <p class="mt-4 text-sm font-medium text-slate-400">Загружаем курс и структуру уроков...</p>
    </div>
  </div>

  <div v-else class="mx-auto mt-4 max-w-[1480px] px-0 pb-10 sm:mt-6 sm:px-4">
    <div class="mb-5 flex flex-col gap-4 rounded-3xl border border-slate-800/80 bg-slate-900/65 p-4 shadow-2xl shadow-slate-950/20 sm:p-5 lg:flex-row lg:items-center lg:justify-between">
      <div class="min-w-0">
        <button
          class="mb-4 inline-flex max-w-full items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-950/30 px-3 py-2 text-sm font-semibold text-slate-300 transition hover:border-indigo-400/60 hover:text-white"
          @click="router.push({ name: 'course-detail', params: { id: courseId } })"
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          Описание курса
        </button>
        <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300/80">Прохождение курса</p>
        <h1 class="mt-2 line-clamp-2 text-2xl font-black text-slate-100 sm:text-3xl">{{ outline?.title }}</h1>
      </div>

      <div class="grid gap-3 sm:grid-cols-3 lg:min-w-[420px]">
        <div class="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Прогресс</p>
          <p class="mt-1 text-2xl font-black text-slate-100">{{ progressPercent }}%</p>
        </div>
        <div class="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Пройдено</p>
          <p class="mt-1 text-2xl font-black text-emerald-300">{{ completedLessons }}/{{ totalLessons }}</p>
        </div>
        <div class="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3">
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Доступно</p>
          <p class="mt-1 text-2xl font-black text-indigo-300">{{ availableLessons }}</p>
        </div>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[360px,minmax(0,1fr)]">
      <aside class="h-fit min-w-0 rounded-3xl border border-slate-800/80 bg-slate-900/70 p-4 shadow-2xl shadow-slate-950/20 lg:sticky lg:top-24">
        <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-lg font-black text-slate-100">Содержание</h2>
            <p class="text-sm text-slate-500">Модули и уроки курса</p>
          </div>
          <div class="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-200">
            {{ modules.length }} мод.
          </div>
        </div>

        <div class="mb-4 h-2 overflow-hidden rounded-full bg-slate-950">
          <div class="h-full rounded-full bg-indigo-500 transition-all duration-500" :style="{ width: `${progressPercent}%` }"></div>
        </div>

        <div v-if="modules.length" class="max-h-[52vh] space-y-3 overflow-y-auto pr-1 lg:max-h-[calc(100vh-190px)]">
          <div
            v-for="(moduleItem, moduleIndex) in modules"
            :key="moduleItem.id"
            class="overflow-hidden rounded-2xl border transition"
            :class="activeModuleId === moduleItem.id
              ? 'border-indigo-400/45 bg-indigo-500/[0.07] shadow-lg shadow-indigo-950/20'
              : 'border-slate-800 bg-slate-950/35'"
          >
            <button
              class="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-slate-800/35 sm:px-4"
              @click="toggleModule(moduleItem.id)"
            >
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span
                    class="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl border text-xs font-black"
                    :class="activeModuleId === moduleItem.id
                      ? 'border-indigo-300/40 bg-indigo-400/15 text-indigo-100'
                      : 'border-slate-700 bg-slate-900 text-slate-400'"
                  >
                    {{ moduleIndex + 1 }}
                  </span>
                  <span class="line-clamp-2 text-sm font-bold text-slate-100">{{ moduleItem.title }}</span>
                </div>
                <div class="mt-2 flex items-center gap-2 pl-9">
                  <div class="h-1.5 w-20 overflow-hidden rounded-full bg-slate-900">
                    <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${moduleProgress(moduleItem)}%` }"></div>
                  </div>
                  <span class="text-[11px] font-semibold text-slate-500">{{ moduleProgress(moduleItem) }}%</span>
                </div>
              </div>

              <svg
                class="h-4 w-4 shrink-0 text-slate-500 transition-transform"
                :class="expandedModules[moduleItem.id] ? 'rotate-180' : ''"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>

            <div v-if="expandedModules[moduleItem.id]" class="max-h-72 space-y-2 overflow-y-auto border-t border-slate-800/90 p-2.5 lg:max-h-none lg:overflow-visible">
              <button
                v-for="(lesson, lessonIndex) in moduleItem.lessons"
                :key="lesson.id"
                class="group relative flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left transition"
                :class="[
                  selectedLessonId === lesson.id
                    ? 'border-indigo-400/70 bg-indigo-500/15 shadow-lg shadow-indigo-950/20'
                    : lessonStatusClass(lesson),
                  lesson.is_locked ? 'cursor-not-allowed opacity-80' : 'hover:border-indigo-400/60 hover:bg-indigo-500/10',
                ]"
                @click="selectLesson(lesson, moduleItem.id)"
              >
                <span
                  class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border"
                  :class="selectedLessonId === lesson.id
                    ? 'border-indigo-300/50 bg-indigo-500/20 text-indigo-100'
                    : 'border-slate-700 bg-slate-950/60 text-slate-400'"
                >
                  <svg v-if="lesson.type === 'video'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M8 6.5v11l9-5.5-9-5.5z" fill="currentColor" />
                    <path d="M4 5.75C4 4.78 4.78 4 5.75 4h12.5C19.22 4 20 4.78 20 5.75v12.5c0 .97-.78 1.75-1.75 1.75H5.75C4.78 20 4 19.22 4 18.25V5.75z" stroke="currentColor" stroke-width="1.6" />
                  </svg>
                  <svg v-else-if="lesson.type === 'quiz'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M8 7h8M8 12h8M8 17h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                    <path d="M5 4h14v16H5V4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                  </svg>
                  <svg v-else-if="lesson.type === 'final_exam'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 3l7 4v5c0 4.2-2.9 7.2-7 9-4.1-1.8-7-4.8-7-9V7l7-4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                    <path d="M9 12l2 2 4-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                  <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M7 4h10v16H7V4z" stroke="currentColor" stroke-width="1.6" />
                    <path d="M9 8h6M9 12h6M9 16h4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                  </svg>
                </span>

                <span class="min-w-0 flex-1">
                  <span class="block line-clamp-2 text-sm font-bold text-slate-100">{{ lesson.title }}</span>
                  <span class="mt-1 flex flex-wrap items-center gap-2 text-[11px] font-semibold text-slate-500">
                    <span>{{ moduleIndex + 1 }}.{{ lessonIndex + 1 }}</span>
                    <span class="h-1 w-1 rounded-full bg-slate-700"></span>
                    <span>{{ lessonTypeLabel(lesson.type) }}</span>
                  </span>
                </span>

                <span class="shrink-0" :title="lessonStatusLabel(lesson)">
                  <svg v-if="lesson.is_completed" class="h-5 w-5 text-emerald-300" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                  <svg v-else-if="lesson.is_locked" class="h-5 w-5 text-slate-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M7 10V8a5 5 0 0110 0v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                    <path d="M6 10h12v10H6V10z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                  </svg>
                  <svg v-else class="h-5 w-5 text-indigo-300" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M8 5v14l11-7L8 5z" fill="currentColor" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
        </div>

        <div v-else class="rounded-2xl border border-slate-800 bg-slate-950/40 p-5 text-sm text-slate-400">
          В этом курсе пока нет опубликованных уроков.
        </div>
      </aside>

      <main class="min-w-0 rounded-3xl border border-slate-800/80 bg-slate-900/70 p-2 shadow-2xl shadow-slate-950/20 sm:p-4">
        <div v-if="selectedLesson" class="mb-3 rounded-2xl border border-slate-800 bg-slate-950/35 px-4 py-3">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div class="min-w-0">
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">
                Модуль {{ activeModuleIndex + 1 }} · {{ lessonTypeLabel(selectedLesson.type) }}
              </p>
              <h2 class="mt-1 line-clamp-2 text-lg font-black text-slate-100">{{ selectedLesson.title }}</h2>
            </div>
            <span
              class="inline-flex w-fit items-center rounded-full border px-3 py-1 text-xs font-bold"
              :class="selectedLesson.is_completed
                ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
                : 'border-indigo-400/30 bg-indigo-500/10 text-indigo-200'"
            >
              {{ lessonStatusLabel(selectedLesson) }}
            </span>
          </div>
        </div>

        <LessonView
          v-if="selectedLessonId"
          :lesson-id="selectedLessonId"
          :embedded="true"
          @lesson-updated="fetchOutline"
        />
        <div v-else class="flex min-h-[55vh] items-center justify-center rounded-3xl border border-dashed border-slate-800 bg-slate-950/30 px-6 text-center text-slate-400">
          <div>
            <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-slate-500">
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 4h14v16H5V4z" stroke="currentColor" stroke-width="1.6" />
                <path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
              </svg>
            </div>
            <p class="font-semibold text-slate-300">Доступных уроков пока нет</p>
            <p class="mt-1 text-sm text-slate-500">Когда преподаватель опубликует уроки, они появятся здесь.</p>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
