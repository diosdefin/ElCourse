<script setup>
import { computed, onMounted, ref } from 'vue'
import HeroAnimation from '../components/HeroAnimation.vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const courses = ref([])
const loading = ref(true)
const loadError = ref('')

const roleCards = [
  {
    title: 'Студент',
    text: 'Проходит курсы, сдаёт тесты, собирает подтверждённые навыки и формирует учебный профиль.',
  },
  {
    title: 'Преподаватель',
    text: 'Создаёт модули, уроки, тесты, материалы и управляет структурой курса в едином конструкторе.',
  },
  {
    title: 'Работодатель',
    text: 'Находит кандидатов по навыкам, просматривает профиль и отправляет карьерные предложения.',
  },
]

const advantages = [
  {
    title: 'Модульное обучение',
    text: 'Курс строится из модулей и уроков, поэтому учебный путь остаётся понятным и последовательным.',
  },
  {
    title: 'Видео и материалы',
    text: 'Видеоуроки, HLS-обработка, текстовые материалы и вложения доступны в одном интерфейсе.',
  },
  {
    title: 'Проверка знаний',
    text: 'Тесты и финальные экзамены помогают подтверждать результат, а не просто фиксировать просмотр.',
  },
  {
    title: 'Карьерный профиль',
    text: 'Навыки, активность и публичный профиль связывают обучение с дальнейшим трудоустройством.',
  },
]

const featuredCourses = computed(() => courses.value.slice(0, 3))
const courseCount = computed(() => courses.value.length)
const skillCount = computed(() => {
  const uniqueSkills = new Set()
  for (const course of courses.value) {
    for (const skill of course.skills_covered || []) {
      if (skill?.name) uniqueSkills.add(skill.name)
    }
  }
  return uniqueSkills.size
})

const profileTarget = computed(() => (authStore.isAuthenticated ? '/profile' : '/login'))
const profileButtonText = computed(() => (authStore.isAuthenticated ? 'Открыть профиль' : 'Войти в систему'))

onMounted(async () => {
  try {
    const response = await api.get('/courses/')
    courses.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
    loadError.value = 'Не удалось загрузить каталог курсов.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="pb-14">
    <section class="relative overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900/70 shadow-2xl shadow-slate-950/30">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,rgba(99,102,241,0.22),transparent_34%),radial-gradient(circle_at_82%_16%,rgba(20,184,166,0.16),transparent_30%)]"></div>
      <div class="relative grid gap-10 px-6 py-10 sm:px-8 lg:grid-cols-[1.05fr,0.95fr] lg:px-12 lg:py-14">
        <div class="flex flex-col justify-center">
          <div class="inline-flex w-fit items-center rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.24em] text-indigo-200">
            Платформа профессионального обучения
          </div>

          <h1 class="mt-6 max-w-3xl text-4xl font-black leading-[1.08] text-white sm:text-5xl lg:text-6xl">
            ElCourse объединяет обучение, навыки и карьерный рост.
          </h1>

          <p class="mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
            Учебная платформа для курсов, тестов, подтверждённых компетенций и взаимодействия студентов с работодателями.
          </p>

          <div class="mt-8 flex flex-wrap gap-3">
            <RouterLink
              to="/courses"
              class="inline-flex items-center justify-center rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500"
            >
              Смотреть курсы
            </RouterLink>
            <RouterLink
              to="/login"
              class="inline-flex items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/30 px-6 py-3 text-sm font-bold text-slate-100 transition hover:border-slate-500 hover:bg-slate-900"
            >
              Войти / Регистрация
            </RouterLink>
          </div>

          <div class="mt-9 grid max-w-2xl grid-cols-3 gap-3">
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Курсы</p>
              <p class="mt-2 text-2xl font-black text-white">{{ courseCount }}</p>
            </div>
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Навыки</p>
              <p class="mt-2 text-2xl font-black text-white">{{ skillCount }}</p>
            </div>
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">Роли</p>
              <p class="mt-2 text-2xl font-black text-white">3</p>
            </div>
          </div>
        </div>

        <div class="relative flex flex-col justify-center">
          <div class="pointer-events-none absolute inset-6 rounded-full bg-indigo-500/10 blur-3xl"></div>
          <div class="relative rounded-[1.8rem] border border-slate-800 bg-slate-950/35 p-5 backdrop-blur">
            <HeroAnimation />
          </div>
          <div class="relative mt-4 rounded-[1.5rem] border border-slate-800 bg-slate-950/50 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Рабочий процесс</p>
            <div class="mt-4 grid gap-3 sm:grid-cols-3">
              <div class="rounded-2xl bg-slate-900/80 p-4">
                <p class="text-sm font-black text-white">Курс</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">Модули, уроки и материалы.</p>
              </div>
              <div class="rounded-2xl bg-slate-900/80 p-4">
                <p class="text-sm font-black text-white">Проверка</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">Quiz и итоговый экзамен.</p>
              </div>
              <div class="rounded-2xl bg-slate-900/80 p-4">
                <p class="text-sm font-black text-white">Профиль</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">Навыки и активность.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mt-8 grid gap-4 lg:grid-cols-3">
      <article
        v-for="role in roleCards"
        :key="role.title"
        class="rounded-[1.5rem] border border-slate-800 bg-slate-900/60 p-6 transition hover:border-slate-700 hover:bg-slate-900/80"
      >
        <p class="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Роль</p>
        <h2 class="mt-3 text-2xl font-black text-white">{{ role.title }}</h2>
        <p class="mt-3 text-sm leading-7 text-slate-400">{{ role.text }}</p>
      </article>
    </section>

    <section class="mt-8 rounded-[2rem] border border-slate-800 bg-slate-900/55 p-6 sm:p-8">
      <div class="max-w-3xl">
        <p class="text-xs font-bold uppercase tracking-[0.24em] text-emerald-300">Возможности</p>
        <h2 class="mt-3 text-3xl font-black text-white">Функции, которые нужны для учебного прототипа</h2>
        <p class="mt-3 text-sm leading-7 text-slate-400">
          Интерфейс показывает полный цикл: создание курса, прохождение уроков, проверка знаний и формирование профиля навыков.
        </p>
      </div>

      <div class="mt-7 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <article
          v-for="advantage in advantages"
          :key="advantage.title"
          class="rounded-[1.3rem] border border-slate-800 bg-slate-950/35 p-5"
        >
          <div class="mb-4 h-1.5 w-10 rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400"></div>
          <h3 class="text-lg font-black text-white">{{ advantage.title }}</h3>
          <p class="mt-3 text-sm leading-6 text-slate-400">{{ advantage.text }}</p>
        </article>
      </div>
    </section>

    <section class="mt-8 rounded-[2rem] border border-slate-800 bg-slate-900/55 p-6 sm:p-8">
      <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Каталог</p>
          <h2 class="mt-3 text-3xl font-black text-white">Доступные курсы</h2>
          <p class="mt-3 max-w-2xl text-sm leading-7 text-slate-400">
            Выберите программу, изучайте материалы, проходите тесты и фиксируйте прогресс в профиле.
          </p>
        </div>
        <RouterLink
          to="/courses"
          class="inline-flex w-fit items-center justify-center rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
        >
          Открыть все курсы
        </RouterLink>
      </div>

      <div v-if="loading" class="mt-7 grid gap-4 lg:grid-cols-3">
        <div v-for="item in 3" :key="item" class="h-72 animate-pulse rounded-[1.5rem] border border-slate-800 bg-slate-950/35"></div>
      </div>

      <div v-else-if="loadError" class="mt-7 rounded-[1.5rem] border border-rose-500/20 bg-rose-500/10 p-6 text-sm text-rose-100">
        {{ loadError }}
      </div>

      <div v-else-if="!featuredCourses.length" class="mt-7 rounded-[1.5rem] border border-slate-800 bg-slate-950/35 p-8 text-center">
        <h3 class="text-xl font-black text-white">Курсы пока не опубликованы</h3>
        <p class="mt-2 text-sm text-slate-400">После добавления курсов они появятся в этом каталоге.</p>
      </div>

      <div v-else class="mt-7 grid gap-5 lg:grid-cols-3">
        <article
          v-for="course in featuredCourses"
          :key="course.id"
          class="group overflow-hidden rounded-[1.5rem] border border-slate-800 bg-slate-950/40 transition hover:-translate-y-1 hover:border-slate-700"
        >
          <div class="relative h-40 overflow-hidden border-b border-slate-800 bg-slate-900">
            <div
              v-if="course.image"
              class="absolute inset-0 bg-cover bg-center opacity-80 transition duration-500 group-hover:scale-105"
              :style="`background-image: url(${course.image})`"
            ></div>
            <div v-else class="absolute inset-0 bg-gradient-to-br from-indigo-600/35 via-slate-900 to-slate-950"></div>
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent"></div>
            <div class="absolute bottom-4 left-4 right-4 flex flex-wrap gap-2">
              <span
                v-for="skill in (course.skills_covered || []).slice(0, 3)"
                :key="skill.id || skill.name"
                class="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold text-white backdrop-blur"
              >
                {{ skill.name }}
              </span>
            </div>
          </div>

          <div class="p-5">
            <h3 class="line-clamp-2 text-xl font-black text-white">{{ course.title }}</h3>
            <p class="mt-3 line-clamp-3 text-sm leading-6 text-slate-400">{{ course.description || 'Описание курса будет добавлено позже.' }}</p>
            <div class="mt-5 flex items-center justify-between border-t border-slate-800 pt-4 text-xs uppercase tracking-[0.16em] text-slate-500">
              <span>Автор</span>
              <span class="text-slate-300">{{ course.author_name || 'Автор курса' }}</span>
            </div>
            <RouterLink
              :to="{ name: 'course-detail', params: { id: course.id } }"
              class="mt-5 block rounded-2xl bg-white px-4 py-3 text-center text-sm font-bold text-slate-950 transition hover:bg-slate-200"
            >
              Открыть курс
            </RouterLink>
          </div>
        </article>
      </div>
    </section>

    <section class="mt-8 overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950 p-8 text-center sm:p-10">
      <p class="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Начните работу</p>
      <h2 class="mx-auto mt-4 max-w-3xl text-3xl font-black leading-tight text-white sm:text-4xl">
        Превратите учебный процесс в понятный профиль компетенций.
      </h2>
      <p class="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-400">
        ElCourse подходит для демонстрации онлайн-обучения, тестирования, активности и карьерной интеграции в одном проекте.
      </p>
      <div class="mt-8 flex flex-wrap justify-center gap-3">
        <RouterLink
          to="/courses"
          class="rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-indigo-500"
        >
          Смотреть курсы
        </RouterLink>
        <RouterLink
          to="/login"
          class="rounded-2xl border border-slate-700 px-6 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
        >
          Войти / Регистрация
        </RouterLink>
      </div>
    </section>
  </div>
</template>
