<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError } from '../utils/toast'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const courses = ref([])
const loading = ref(true)
const loadError = ref('')
const searchInput = ref('')
const search = ref('')

// ========== 专业筛选面板 - 全新状态 ==========
const selectedSkills = ref([])         // Массив выбранных навыков (OR-логика)
const selectedAuthors = ref([])        // Массив выбранных авторов
const lessonMin = ref(0)               // Мин. кол-во уроков
const lessonMax = ref(100)             // Макс. кол-во уроков
const sortMode = ref('recommended')
const activeTab = ref('catalog')
const currentPage = ref(1)
const pageSize = 12
let searchTimer = null

// Глобальные min/max уроков (из всех курсов)
const globalMinLessons = computed(() => {
  if (!courses.value.length) return 0
  return Math.min(...courses.value.map(c => lessonCountOf(c)))
})
const globalMaxLessons = computed(() => {
  if (!courses.value.length) return 0
  return Math.max(...courses.value.map(c => lessonCountOf(c)))
})

// Список всех авторов (уникальные имена)
const allAuthors = computed(() => {
  const authorsSet = new Set()
  for (const course of courses.value) {
    if (course.author_name && course.author_name.trim()) {
      authorsSet.add(course.author_name)
    }
  }
  return Array.from(authorsSet).sort((a, b) => a.localeCompare(b, 'ru'))
})

// Список всех навыков (уникальные названия)
const allSkills = computed(() => {
  const map = new Map()
  for (const course of courses.value) {
    for (const skill of course.skills_covered || []) {
      const name = skill?.name || skill
      if (name && !map.has(name)) map.set(name, skill?.id || name)
    }
  }
  return Array.from(map.entries())
    .map(([name, id]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, 'ru'))
})

// ==========  вспомогательные функции ==========
const normalizeText = (value) => String(value || '').trim().toLowerCase()
const lessonsOf = (course) => (Array.isArray(course?.lessons) ? course.lessons : [])
const progressOf = (course) => Number(course?.progress_percentage || 0)
const completedLessonsOf = (course) => lessonsOf(course).filter((lesson) => lesson?.is_completed).length
const lessonCountOf = (course) => lessonsOf(course).length
const hasStartedCourse = (course) => progressOf(course) > 0 || completedLessonsOf(course) > 0
const hasLessonFlow = (course) => lessonCountOf(course) > 0

// ==========  табы ==========
const availableTabs = computed(() => {
  const tabs = [{ key: 'catalog', label: 'Все курсы' }]
  if (authStore.isAuthenticated && authStore.isStudent) {
    tabs.push(
      { key: 'my', label: 'Мои курсы' },
      { key: 'continue', label: 'Продолжить' }
    )
  }
  return tabs
})

const myCourses = computed(() => courses.value.filter((course) => hasStartedCourse(course)))
const continueCourses = computed(() => myCourses.value.filter((course) => progressOf(course) < 100))

const sourceCourses = computed(() => {
  if (activeTab.value === 'my') return myCourses.value
  if (activeTab.value === 'continue') return continueCourses.value
  return courses.value
})

// ==========  ОСНОВНАЯ ФИЛЬТРАЦИЯ (профессиональная панель) ==========
const filteredCourses = computed(() => {
  const query = normalizeText(search.value)

  let result = sourceCourses.value.filter((course) => {
    // Текстовый поиск
    const skillNames = (course.skills_covered || []).map((skill) => skill?.name || skill)
    const text = normalizeText([
      course.title,
      course.description,
      course.author_name,
      ...skillNames,
    ].join(' '))
    const matchesSearch = !query || text.includes(query)

    // Фильтр по навыкам (OR — достаточно одного совпадения)
    let matchesSkill = true
    if (selectedSkills.value.length > 0) {
      const courseSkills = skillNames.map(s => s.toLowerCase())
      matchesSkill = selectedSkills.value.some(skill =>
        courseSkills.includes(skill.toLowerCase())
      )
    }

    // Фильтр по автору
    let matchesAuthor = true
    if (selectedAuthors.value.length > 0) {
      const author = course.author_name || ''
      matchesAuthor = selectedAuthors.value.includes(author)
    }

    // Фильтр по количеству уроков
    const lessonCount = lessonCountOf(course)
    const matchesLessonRange = lessonCount >= lessonMin.value && lessonCount <= lessonMax.value

    return matchesSearch && matchesSkill && matchesAuthor && matchesLessonRange
  })

  // Сортировка
  const sorted = [...result]
  if (sortMode.value === 'title') {
    sorted.sort((a, b) => String(a.title || '').localeCompare(String(b.title || ''), 'ru'))
  } else if (sortMode.value === 'progress') {
    sorted.sort((a, b) => progressOf(b) - progressOf(a))
  } else if (sortMode.value === 'lessons') {
    sorted.sort((a, b) => lessonCountOf(b) - lessonCountOf(a))
  } else {
    sorted.sort((a, b) => {
      const progressDiff = progressOf(b) - progressOf(a)
      if (progressDiff !== 0) return progressDiff
      return lessonCountOf(b) - lessonCountOf(a)
    })
  }
  return sorted
})

// ==========  статистика для панели ==========
const totalCourses = computed(() => courses.value.length)
const activeCoursesCount = computed(() => myCourses.value.length)
const completedCoursesCount = computed(() => myCourses.value.filter((course) => progressOf(course) >= 100).length)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredCourses.value.length / pageSize)))
const pageStart = computed(() => (currentPage.value - 1) * pageSize)
const paginatedCourses = computed(() => filteredCourses.value.slice(pageStart.value, pageStart.value + pageSize))

const emptyTitle = computed(() => {
  if (activeTab.value === 'my') return 'Активных курсов пока нет'
  if (activeTab.value === 'continue') return 'Нет курсов для продолжения'
  return 'Курсы не найдены'
})
const emptyText = computed(() => {
  if (search.value || selectedSkills.value.length || selectedAuthors.value.length ||
    lessonMin.value !== globalMinLessons.value || lessonMax.value !== globalMaxLessons.value)
    return 'Попробуйте изменить запрос или сбросить фильтры.'
  if (activeTab.value === 'my') return 'Начните курс из каталога, и он появится в этом разделе.'
  if (activeTab.value === 'continue') return 'Начатые, но не завершённые курсы появятся здесь.'
  return 'После публикации курсов преподавателями они появятся на странице.'
})

// ==========  действия с курсами ==========
const actionLabel = (course) => {
  if (!authStore.isAuthenticated) return 'Подробнее'
  if (!hasLessonFlow(course)) return 'Подробнее'
  if (progressOf(course) > 0 && progressOf(course) < 100) return 'Продолжить'
  if (progressOf(course) >= 100) return 'Повторить'
  return 'Начать'
}
const actionTarget = (course) => {
  if (authStore.isAuthenticated && hasLessonFlow(course)) {
    return { name: 'course-play', params: { id: course.id } }
  }
  return { name: 'course-detail', params: { id: course.id } }
}

// ==========  управление фильтрами и состоянием ==========
const setTab = (tab) => {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

const toggleSkill = (skillName) => {
  const index = selectedSkills.value.indexOf(skillName)
  if (index === -1) {
    selectedSkills.value.push(skillName)
  } else {
    selectedSkills.value.splice(index, 1)
  }
}

const toggleAuthor = (authorName) => {
  const index = selectedAuthors.value.indexOf(authorName)
  if (index === -1) {
    selectedAuthors.value.push(authorName)
  } else {
    selectedAuthors.value.splice(index, 1)
  }
}

const clearFilters = () => {
  searchInput.value = ''
  search.value = ''
  selectedSkills.value = []
  selectedAuthors.value = []
  lessonMin.value = globalMinLessons.value
  lessonMax.value = globalMaxLessons.value
  sortMode.value = 'recommended'
}

const loadCourses = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const response = await api.get('/courses/')
    const data = response.data
    courses.value = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
    // Установка границ количества уроков после загрузки
    lessonMin.value = globalMinLessons.value
    lessonMax.value = globalMaxLessons.value
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
    loadError.value = 'Не удалось загрузить каталог курсов.'
    showError('Не удалось загрузить каталог курсов.')
  } finally {
    loading.value = false
  }
}

// ==========  watchers ==========
watch(searchInput, (value) => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    search.value = value
  }, 320)
})

watch(
  () => route.query.tab,
  (tab) => {
    const normalized = String(tab || 'catalog')
    const exists = availableTabs.value.some((item) => item.key === normalized)
    activeTab.value = exists ? normalized : 'catalog'
  },
  { immediate: true }
)

watch(
  () => availableTabs.value.map((item) => item.key).join(','),
  () => {
    if (!availableTabs.value.some((item) => item.key === activeTab.value)) {
      activeTab.value = 'catalog'
    }
  }
)

watch([search, selectedSkills, selectedAuthors, lessonMin, lessonMax, sortMode, activeTab], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

onMounted(loadCourses)
</script>

<template>
  <div class="mx-auto max-w-[1440px] px-4 pb-12 pt-5 sm:px-6 lg:px-8">
    <header class="border-b border-slate-800/80 pb-5">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="min-w-0">

          <h1 class="mt-3 text-[30px] font-black leading-none tracking-tight text-white sm:text-[38px]">
            Все онлайн-курсы
          </h1>
        </div>

        <div
          class="grid w-full grid-cols-3 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/30 lg:w-[360px]">
          <div class="border-r border-slate-800 px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">Курсы</p>
            <p class="mt-1 text-xl font-black text-white">{{ totalCourses }}</p>
          </div>
          <div class="border-r border-slate-800 px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">Активные</p>
            <p class="mt-1 text-xl font-black text-emerald-300">{{ activeCoursesCount }}</p>
          </div>
          <div class="px-4 py-3">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-500">Готово</p>
            <p class="mt-1 text-xl font-black text-white">{{ completedCoursesCount }}</p>
          </div>
        </div>
      </div>

      <div class="mt-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div class="flex gap-2 overflow-x-auto pb-1">
          <button v-for="tab in availableTabs" :key="tab.key" type="button"
            class="shrink-0 rounded-full border px-4 py-2 text-xs font-black transition" :class="activeTab === tab.key
              ? 'border-indigo-400/60 bg-indigo-500 text-white shadow-lg shadow-indigo-500/15'
              : 'border-slate-700 bg-slate-950/20 text-slate-300 hover:border-slate-500 hover:text-white'"
            @click="setTab(tab.key)">
            {{ tab.label }}
          </button>
        </div>

        <label class="relative block w-full xl:w-[520px]">
          <span class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M10.8 18.1a7.3 7.3 0 100-14.6 7.3 7.3 0 000 14.6zM16.2 16.2L21 21" stroke="currentColor"
                stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>
          <input v-model="searchInput" type="search"
            class="h-10 w-full rounded-full border border-slate-800 bg-slate-950/35 px-4 pl-10 text-sm font-semibold text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400/70 focus:bg-slate-950/60"
            placeholder="Поиск курса, автора или навыка">
        </label>
      </div>

      <!-- Быстрые чипсы навыков -->
      <div v-if="allSkills.length" class="mt-4 flex gap-2 overflow-x-auto pb-1">
        <button type="button" class="shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-black transition" :class="selectedSkills.length === 0
          ? 'border-indigo-400/60 bg-indigo-500 text-white'
          : 'border-slate-700 bg-slate-950/20 text-slate-300 hover:border-slate-500 hover:text-white'"
          @click="selectedSkills = []">
          Все направления
        </button>
        <button v-for="skill in allSkills" :key="skill.id" type="button"
          class="shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-black transition" :class="selectedSkills.includes(skill.name)
            ? 'border-indigo-400/60 bg-indigo-500 text-white'
            : 'border-slate-700 bg-slate-950/20 text-slate-300 hover:border-slate-500 hover:text-white'"
          @click="toggleSkill(skill.name)">
          {{ skill.name }}
        </button>
      </div>
    </header>

    <div class="mt-6 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
      <!-- ========== ПРОФЕССИОНАЛЬНАЯ ПАНЕЛЬ ФИЛЬТРОВ (левая колонка) ========== -->
      <aside
        class="self-start rounded-2xl border border-slate-800 bg-slate-950/40 p-5 backdrop-blur-sm lg:sticky lg:top-24">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <svg class="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            <p class="text-[12px] font-black uppercase tracking-[0.22em] text-slate-300">Фильтры</p>
          </div>
          <button type="button" class="text-xs font-bold text-slate-400 transition hover:text-indigo-300"
            @click="clearFilters">
            Сбросить все
          </button>
        </div>

        <!-- Раздел (табы) внутри панели -->
        <div class="mt-4 border-t border-slate-800 pt-4">
          <p class="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Категория курсов</p>
          <div class="space-y-1">
            <button v-for="tab in availableTabs" :key="tab.key" type="button"
              class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-bold transition"
              :class="activeTab === tab.key
                ? 'bg-indigo-500/20 text-indigo-200 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-white'" @click="setTab(tab.key)">
              <span>{{ tab.label }}</span>
              <span class="text-xs opacity-70">
                {{ tab.key === 'catalog' ? totalCourses : tab.key === 'my' ? activeCoursesCount : continueCourses.length
                }}
              </span>
            </button>
          </div>
        </div>

        <!-- Навыки (мультивыбор) -->
        <div class="mt-5 border-t border-slate-800 pt-4">
          <p class="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Навыки</p>
          <div class="max-h-48 space-y-1.5 overflow-y-auto pr-1 custom-scroll">
            <label v-for="skill in allSkills" :key="skill.id"
              class="flex cursor-pointer items-center justify-between rounded-lg px-2 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800/50">
              <span>{{ skill.name }}</span>
              <input type="checkbox"
                class="h-3.5 w-3.5 rounded border-slate-600 bg-slate-900 text-indigo-500 focus:ring-indigo-500/20 focus:ring-offset-0"
                :checked="selectedSkills.includes(skill.name)" @change="toggleSkill(skill.name)">
            </label>
          </div>
        </div>

        <!-- Авторы -->
        <div v-if="allAuthors.length" class="mt-5 border-t border-slate-800 pt-4">
          <p class="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Авторы</p>
          <div class="max-h-40 space-y-1.5 overflow-y-auto pr-1 custom-scroll">
            <label v-for="author in allAuthors" :key="author"
              class="flex cursor-pointer items-center justify-between rounded-lg px-2 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-slate-800/50">
              <span class="truncate">{{ author }}</span>
              <input type="checkbox"
                class="h-3.5 w-3.5 rounded border-slate-600 bg-slate-900 text-indigo-500 focus:ring-indigo-500/20"
                :checked="selectedAuthors.includes(author)" @change="toggleAuthor(author)">
            </label>
          </div>
        </div>

        <!-- Количество уроков (диапазон) -->
        <div class="mt-5 border-t border-slate-800 pt-4">
          <p class="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Уроков: {{ lessonMin }} – {{
            lessonMax }}</p>
          <div class="flex items-center gap-3">
            <input v-model.number="lessonMin" type="number" :min="globalMinLessons" :max="globalMaxLessons"
              class="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-sm font-semibold text-slate-100 outline-none focus:border-indigo-400" />
            <span class="text-slate-500">—</span>
            <input v-model.number="lessonMax" type="number" :min="globalMinLessons" :max="globalMaxLessons"
              class="w-full rounded-lg border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-sm font-semibold text-slate-100 outline-none focus:border-indigo-400" />
          </div>
          <div class="mt-2 flex justify-between text-[10px] text-slate-500">
            <span>мин: {{ globalMinLessons }}</span>
            <span>макс: {{ globalMaxLessons }}</span>
          </div>
        </div>

        <!-- Сортировка -->
        <div class="mt-5 border-t border-slate-800 pt-4">
          <p class="mb-2 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Сортировка</p>
          <select v-model="sortMode"
            class="h-9 w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 text-sm font-bold text-slate-100 outline-none focus:border-indigo-400/70">
            <option value="recommended">Рекомендуемые</option>
            <option value="progress">По прогрессу</option>
            <option value="lessons">По урокам</option>
            <option value="title">По названию</option>
          </select>
        </div>

        <div class="mt-6 rounded-xl bg-indigo-500/5 p-3 text-center text-[11px] leading-relaxed text-slate-400">
          {{ selectedSkills.length }} навыков, {{ selectedAuthors.length }} авторов
        </div>
      </aside>

      <!-- Основной контент (карточки курсов) -->
      <main class="min-w-0">
        <div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm font-semibold text-slate-400">
            Найдено: <span class="text-white">{{ filteredCourses.length }}</span>
          </p>
          <p class="text-xs font-semibold text-slate-500">
            Страница {{ currentPage }} из {{ totalPages }}
          </p>
        </div>

        <section v-if="loading" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div v-for="item in 9" :key="item"
            class="h-[260px] animate-pulse rounded-2xl border border-slate-800 bg-slate-900/50"></div>
        </section>

        <section v-else-if="loadError" class="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-8 text-center">
          <h3 class="text-lg font-black text-rose-100">Не удалось загрузить данные</h3>
          <p class="mt-2 text-sm text-rose-200/80">{{ loadError }}</p>
          <button type="button"
            class="mt-5 rounded-xl bg-rose-500 px-5 py-2.5 text-sm font-black text-white transition hover:bg-rose-400"
            @click="loadCourses">
            Повторить
          </button>
        </section>

        <section v-else-if="!filteredCourses.length"
          class="rounded-2xl border border-slate-800 bg-slate-950/25 p-10 text-center">
          <h3 class="text-xl font-black text-white">{{ emptyTitle }}</h3>
          <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">{{ emptyText }}</p>
          <button
            v-if="search || selectedSkills.length || selectedAuthors.length || lessonMin !== globalMinLessons || lessonMax !== globalMaxLessons"
            type="button"
            class="mt-5 rounded-xl border border-slate-700 px-5 py-2.5 text-sm font-black text-slate-200 transition hover:border-slate-500 hover:text-white"
            @click="clearFilters">
            Сбросить фильтры
          </button>
        </section>

        <section v-else class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <article v-for="course in paginatedCourses" :key="course.id"
            class="group overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/45 transition hover:-translate-y-0.5 hover:border-slate-600 hover:bg-slate-900/70">
            <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }" class="block">
              <div class="relative h-28 overflow-hidden bg-slate-950 sm:h-32">
                <img v-if="course.image" :src="$media(course.image)" :alt="course.title"
                  class="h-full w-full object-cover opacity-85 transition duration-500 group-hover:scale-105 group-hover:opacity-100">
                <div v-else
                  class="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950/60 text-slate-600">
                  <svg class="h-10 w-10" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M4 6.5A2.5 2.5 0 016.5 4h11A2.5 2.5 0 0120 6.5v11a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 014 17.5v-11z"
                      stroke="currentColor" stroke-width="1.5" />
                    <path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                </div>

                <div
                  class="absolute left-3 top-3 rounded-full border border-slate-700 bg-slate-950/75 px-2.5 py-1 text-[11px] font-black text-slate-200 backdrop-blur">
                  {{ lessonCountOf(course) }} урок.
                </div>
                <div v-if="hasStartedCourse(course)"
                  class="absolute right-3 top-3 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-black text-emerald-200 backdrop-blur">
                  {{ progressOf(course) }}%
                </div>
              </div>
            </RouterLink>

            <div class="p-4">
              <div class="mb-3 flex flex-wrap gap-1.5">
                <span v-for="skill in (course.skills_covered || []).slice(0, 2)" :key="skill.id || skill.name || skill"
                  class="rounded-full border border-slate-700 bg-slate-950/35 px-2.5 py-1 text-[11px] font-black text-slate-300">
                  {{ skill.name || skill }}
                </span>
              </div>

              <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }" class="block">
                <h3
                  class="line-clamp-2 min-h-[44px] text-base font-black leading-snug text-white transition group-hover:text-indigo-100">
                  {{ course.title }}
                </h3>
              </RouterLink>

              <p class="mt-2 text-xs font-semibold text-slate-500">
                Автор: <span class="text-slate-300">{{ course.author_name || 'Не указан' }}</span>
              </p>
              <p class="mt-3 line-clamp-2 min-h-[40px] text-xs leading-5 text-slate-400">
                {{ course.description || 'Описание курса пока не добавлено.' }}
              </p>

              <div class="mt-4">
                <div
                  class="mb-1.5 flex items-center justify-between text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">
                  <span>Прогресс</span>
                  <span class="text-slate-300">{{ progressOf(course) }}%</span>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-slate-950">
                  <div
                    class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500"
                    :style="{ width: `${progressOf(course)}%` }"></div>
                </div>
              </div>

              <div class="mt-4 grid grid-cols-[1fr_auto] gap-2">
                <RouterLink :to="actionTarget(course)"
                  class="inline-flex h-9 items-center justify-center rounded-xl bg-indigo-500 px-3 text-xs font-black text-white transition hover:bg-indigo-400">
                  {{ actionLabel(course) }}
                </RouterLink>
                <RouterLink :to="{ name: 'course-detail', params: { id: course.id } }"
                  class="inline-flex h-9 items-center justify-center rounded-xl border border-slate-700 px-3 text-xs font-black text-slate-200 transition hover:border-slate-500 hover:text-white">
                  О курсе
                </RouterLink>
              </div>
            </div>
          </article>
        </section>

        <nav v-if="!loading && filteredCourses.length > pageSize" class="mt-6 flex items-center justify-center gap-2">
          <button type="button"
            class="h-9 rounded-xl border border-slate-700 px-4 text-xs font-black text-slate-300 transition hover:border-slate-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="currentPage === 1" @click="currentPage -= 1">
            Назад
          </button>
          <button v-for="page in totalPages" :key="page" type="button"
            class="h-9 min-w-9 rounded-xl border px-3 text-xs font-black transition" :class="page === currentPage
              ? 'border-indigo-400 bg-indigo-500 text-white'
              : 'border-slate-700 text-slate-300 hover:border-slate-500 hover:text-white'" @click="currentPage = page">
            {{ page }}
          </button>
          <button type="button"
            class="h-9 rounded-xl border border-slate-700 px-4 text-xs font-black text-slate-300 transition hover:border-slate-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="currentPage === totalPages" @click="currentPage += 1">
            Вперёд
          </button>
        </nav>
      </main>
    </div>
  </div>
</template>

<style scoped>
.custom-scroll::-webkit-scrollbar {
  width: 4px;
}

.custom-scroll::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 8px;
}

.custom-scroll::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 8px;
}

.custom-scroll::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>
