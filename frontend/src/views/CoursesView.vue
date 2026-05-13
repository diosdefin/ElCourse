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
const search = ref('')
const selectedSkill = ref('all')
const sortMode = ref('recommended')

const availableTabs = computed(() => {
  const tabs = [{ key: 'catalog', label: 'Каталог курсов' }]

  if (authStore.isAuthenticated && authStore.isStudent) {
    tabs.push(
      { key: 'my', label: 'Мои курсы' },
      { key: 'continue', label: 'Продолжить' }
    )
  }

  return tabs
})

const activeTab = ref('catalog')

const mediaUrl = (value) => {
  if (!value) return ''
  if (value.startsWith('http')) return value
  return `http://127.0.0.1:8000${value}`
}

const normalizeText = (value) => String(value || '').trim().toLowerCase()

const lessonsOf = (course) => Array.isArray(course?.lessons) ? course.lessons : []
const progressOf = (course) => Number(course?.progress_percentage || 0)
const completedLessonsOf = (course) => lessonsOf(course).filter((lesson) => lesson?.is_completed).length
const lessonCountOf = (course) => lessonsOf(course).length

const hasStartedCourse = (course) => progressOf(course) > 0 || completedLessonsOf(course) > 0
const hasLessonFlow = (course) => lessonCountOf(course) > 0

const allSkills = computed(() => {
  const map = new Map()

  for (const course of courses.value) {
    for (const skill of course.skills_covered || []) {
      const name = skill?.name || skill
      if (name && !map.has(name)) {
        map.set(name, skill?.id || name)
      }
    }
  }

  return Array.from(map.entries())
    .map(([name, id]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, 'ru'))
})

const catalogCourses = computed(() => courses.value)
const myCourses = computed(() => courses.value.filter((course) => hasStartedCourse(course)))
const continueCourses = computed(() => myCourses.value.filter((course) => progressOf(course) < 100))

const sourceCourses = computed(() => {
  if (activeTab.value === 'my') return myCourses.value
  if (activeTab.value === 'continue') return continueCourses.value
  return catalogCourses.value
})

const filteredCourses = computed(() => {
  const query = normalizeText(search.value)

  let result = sourceCourses.value.filter((course) => {
    const skillNames = (course.skills_covered || []).map((skill) => skill?.name || skill)
    const text = normalizeText([
      course.title,
      course.description,
      course.author_name,
      ...skillNames,
    ].join(' '))

    const matchesSearch = !query || text.includes(query)
    const matchesSkill = selectedSkill.value === 'all' || skillNames.includes(selectedSkill.value)

    return matchesSearch && matchesSkill
  })

  result = [...result]

  if (sortMode.value === 'title') {
    result.sort((a, b) => String(a.title || '').localeCompare(String(b.title || ''), 'ru'))
  } else if (sortMode.value === 'progress') {
    result.sort((a, b) => progressOf(b) - progressOf(a))
  } else if (sortMode.value === 'lessons') {
    result.sort((a, b) => lessonCountOf(b) - lessonCountOf(a))
  } else {
    result.sort((a, b) => {
      const progressDiff = progressOf(b) - progressOf(a)
      if (progressDiff !== 0) return progressDiff
      return lessonCountOf(b) - lessonCountOf(a)
    })
  }

  return result
})

const totalCourses = computed(() => courses.value.length)
const activeCoursesCount = computed(() => myCourses.value.length)
const availableSkillCount = computed(() => allSkills.value.length)
const completedCoursesCount = computed(() => myCourses.value.filter((course) => progressOf(course) >= 100).length)

const headingText = computed(() => {
  if (activeTab.value === 'my') return 'Ваши курсы'
  if (activeTab.value === 'continue') return 'Продолжить обучение'
  return 'Каталог курсов'
})

const descriptionText = computed(() => {
  if (activeTab.value === 'my') {
    return 'Здесь отображаются курсы, где уже есть учебный прогресс. Это позволяет быстро вернуться к активному обучению.'
  }
  if (activeTab.value === 'continue') {
    return 'Курсы, которые уже начаты, но ещё не завершены. Откройте курс и продолжайте с текущего места.'
  }
  return 'Открытый каталог образовательных программ. Выберите курс, изучите описание и начните обучение после входа в аккаунт.'
})

const emptyTitle = computed(() => {
  if (activeTab.value === 'my') return 'Активных курсов пока нет'
  if (activeTab.value === 'continue') return 'Нет курсов для продолжения'
  return 'Курсы не найдены'
})

const emptyText = computed(() => {
  if (search.value || selectedSkill.value !== 'all') return 'Измените фильтр или поисковый запрос.'
  if (activeTab.value === 'my') return 'Откройте каталог и начните первый курс, чтобы он появился здесь.'
  if (activeTab.value === 'continue') return 'Когда вы начнёте курс и ещё не завершите его полностью, он появится в этом разделе.'
  return 'После публикации курсов преподавателями они появятся на этой странице.'
})

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

const setTab = (tab) => {
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
}

const loadCourses = async () => {
  loading.value = true
  loadError.value = ''

  try {
    const response = await api.get('/courses/')
    courses.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
    loadError.value = 'Не удалось загрузить каталог курсов.'
    showError('Не удалось загрузить каталог курсов.')
  } finally {
    loading.value = false
  }
}

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

onMounted(loadCourses)
</script>

<template>
  <div class="pb-14">
    <section class="relative overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900/70 shadow-2xl shadow-slate-950/25">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_12%_10%,rgba(99,102,241,0.2),transparent_32%),radial-gradient(circle_at_86%_18%,rgba(20,184,166,0.14),transparent_28%)]"></div>
      <div class="relative grid gap-8 px-6 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr),360px] lg:px-10 lg:py-10">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.26em] text-indigo-200">ElCourse Learning</p>
          <h1 class="mt-4 max-w-3xl text-3xl font-black leading-tight text-white sm:text-5xl">
            Курсы для обучения, проверки знаний и роста навыков
          </h1>
          <p class="mt-5 max-w-3xl text-sm leading-7 text-slate-400 sm:text-base">
            В одном разделе собраны открытый каталог и личное обучение студента. Страница не перегружает навигацию: каталог, активные курсы и продолжение обучения доступны через вкладки.
          </p>

          <div class="mt-7 flex flex-wrap gap-3">
            <button
              v-for="tab in availableTabs"
              :key="tab.key"
              type="button"
              class="rounded-2xl px-5 py-3 text-sm font-bold transition"
              :class="activeTab === tab.key ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20' : 'border border-slate-700 bg-slate-950/35 text-slate-300 hover:border-slate-500 hover:text-white'"
              @click="setTab(tab.key)"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <div class="rounded-3xl border border-slate-800 bg-slate-950/40 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">Всего курсов</p>
            <p class="mt-2 text-3xl font-black text-white">{{ totalCourses }}</p>
          </div>
          <div class="rounded-3xl border border-slate-800 bg-slate-950/40 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">Навыки</p>
            <p class="mt-2 text-3xl font-black text-emerald-300">{{ availableSkillCount }}</p>
          </div>
          <div v-if="authStore.isAuthenticated && authStore.isStudent" class="rounded-3xl border border-slate-800 bg-slate-950/40 p-5 sm:col-span-2 lg:col-span-1">
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">Моё обучение</p>
            <p class="mt-2 text-sm font-semibold text-slate-300">
              Активных: <span class="text-white">{{ activeCoursesCount }}</span>
              <span class="mx-2 text-slate-700">/</span>
              завершено: <span class="text-emerald-300">{{ completedCoursesCount }}</span>
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="mt-6 rounded-[2rem] border border-slate-800 bg-slate-900/55 p-5 sm:p-6">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Раздел</p>
          <h2 class="mt-2 text-2xl font-black text-white sm:text-3xl">{{ headingText }}</h2>
          <p class="mt-2 max-w-3xl text-sm leading-7 text-slate-400">{{ descriptionText }}</p>
        </div>

        <div class="grid gap-3 sm:grid-cols-[minmax(220px,1fr),180px,190px] xl:w-[720px]">
          <label class="block">
            <span class="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Поиск</span>
            <input
              v-model.trim="search"
              type="search"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-sm font-semibold text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400/70"
              placeholder="Название, автор, навык..."
            >
          </label>

          <label class="block">
            <span class="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Навык</span>
            <select
              v-model="selectedSkill"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-sm font-semibold text-slate-100 outline-none transition focus:border-indigo-400/70"
            >
              <option value="all">Все навыки</option>
              <option v-for="skill in allSkills" :key="skill.id" :value="skill.name">{{ skill.name }}</option>
            </select>
          </label>

          <label class="block">
            <span class="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Сортировка</span>
            <select
              v-model="sortMode"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-sm font-semibold text-slate-100 outline-none transition focus:border-indigo-400/70"
            >
              <option value="recommended">Рекомендуемые</option>
              <option value="progress">По прогрессу</option>
              <option value="lessons">По урокам</option>
              <option value="title">По названию</option>
            </select>
          </label>
        </div>
      </div>
    </section>

    <section v-if="loading" class="mt-6 grid gap-5 lg:grid-cols-3">
      <div v-for="item in 6" :key="item" class="h-96 animate-pulse rounded-[1.7rem] border border-slate-800 bg-slate-900/55"></div>
    </section>

    <section v-else-if="loadError" class="mt-6 rounded-[1.7rem] border border-rose-500/20 bg-rose-500/10 p-8 text-center">
      <h3 class="text-xl font-black text-rose-100">Не удалось загрузить данные</h3>
      <p class="mt-2 text-sm text-rose-200/80">{{ loadError }}</p>
      <button
        type="button"
        class="mt-5 rounded-2xl bg-rose-500 px-6 py-3 text-sm font-bold text-white transition hover:bg-rose-400"
        @click="loadCourses"
      >
        Повторить загрузку
      </button>
    </section>

    <section v-else-if="!filteredCourses.length" class="mt-6 rounded-[1.7rem] border border-slate-800 bg-slate-900/55 p-10 text-center">
      <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/50 text-slate-500">
        <svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M5 4h14v16H5V4z" stroke="currentColor" stroke-width="1.7" />
          <path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
        </svg>
      </div>
      <h3 class="mt-5 text-2xl font-black text-white">{{ emptyTitle }}</h3>
      <p class="mx-auto mt-2 max-w-xl text-sm leading-7 text-slate-400">{{ emptyText }}</p>
      <button
        v-if="search || selectedSkill !== 'all'"
        type="button"
        class="mt-5 rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
        @click="search = ''; selectedSkill = 'all'"
      >
        Сбросить фильтры
      </button>
    </section>

    <section v-else class="mt-6 grid gap-5 lg:grid-cols-3">
      <article
        v-for="course in filteredCourses"
        :key="course.id"
        class="group flex min-h-[420px] flex-col overflow-hidden rounded-[1.7rem] border border-slate-800 bg-slate-900/65 shadow-xl shadow-slate-950/15 transition hover:-translate-y-1 hover:border-slate-700 hover:bg-slate-900"
      >
        <div class="relative h-44 overflow-hidden border-b border-slate-800 bg-slate-950">
          <img
            v-if="course.image"
            :src="mediaUrl(course.image)"
            :alt="course.title"
            class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          >
          <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-950 text-slate-600">
            <svg class="h-16 w-16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 6.5A2.5 2.5 0 016.5 4h11A2.5 2.5 0 0120 6.5v11a2.5 2.5 0 01-2.5 2.5h-11A2.5 2.5 0 014 17.5v-11z" stroke="currentColor" stroke-width="1.5" />
              <path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            </svg>
          </div>

          <div class="absolute left-4 top-4 rounded-full border border-slate-700 bg-slate-950/75 px-3 py-1 text-xs font-bold text-slate-200 backdrop-blur">
            {{ lessonCountOf(course) }} урок.
          </div>
          <div v-if="hasStartedCourse(course)" class="absolute right-4 top-4 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-200 backdrop-blur">
            {{ progressOf(course) }}%
          </div>
        </div>

        <div class="flex flex-1 flex-col p-5">
          <div class="mb-3 flex flex-wrap gap-2">
            <span
              v-for="skill in (course.skills_covered || []).slice(0, 3)"
              :key="skill.id || skill.name || skill"
              class="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-100"
            >
              {{ skill.name || skill }}
            </span>
            <span
              v-if="(course.skills_covered || []).length > 3"
              class="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1 text-xs font-bold text-slate-400"
            >
              +{{ (course.skills_covered || []).length - 3 }}
            </span>
          </div>

          <h3 class="line-clamp-2 text-xl font-black leading-snug text-white">{{ course.title }}</h3>
          <p class="mt-2 text-sm font-semibold text-slate-500">
            Автор: <span class="text-slate-300">{{ course.author_name || 'Не указан' }}</span>
          </p>
          <p class="mt-4 line-clamp-3 text-sm leading-6 text-slate-400">
            {{ course.description || 'Описание курса пока не добавлено.' }}
          </p>

          <div class="mt-5">
            <div class="mb-2 flex items-center justify-between text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
              <span>Прогресс</span>
              <span class="text-slate-300">{{ progressOf(course) }}%</span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-slate-950">
              <div class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500" :style="{ width: `${progressOf(course)}%` }"></div>
            </div>
          </div>

          <div class="mt-auto flex flex-col gap-3 pt-5 sm:flex-row">
            <RouterLink
              :to="actionTarget(course)"
              class="inline-flex flex-1 items-center justify-center rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-indigo-600/15 transition hover:bg-indigo-500"
            >
              {{ actionLabel(course) }}
            </RouterLink>
            <RouterLink
              :to="{ name: 'course-detail', params: { id: course.id } }"
              class="inline-flex items-center justify-center rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
            >
              О курсе
            </RouterLink>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>
