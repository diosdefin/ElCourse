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
    text: 'Проходит курсы, выполняет тесты и формирует профиль подтверждённых навыков.',
  },
  {
    title: 'Преподаватель',
    text: 'Создаёт курсы, уроки и тесты, отслеживает прогресс обучающихся.',
  },
  {
    title: 'Работодатель',
    text: 'Публикует вакансии, ищет кандидатов и анализирует подтверждённые компетенции.',
  },
]

const advantages = [
  {
    title: 'Модульное обучение',
    text: 'Курс собирается из модулей и уроков с понятной структурой.',
  },
  {
    title: 'Видео и материалы',
    text: 'Видео, текстовые материалы и вложения доступны в одном интерфейсе.',
  },
  {
    title: 'Проверка знаний',
    text: 'Quiz и итоговые проверки подтверждают освоение материала.',
  },
  {
    title: 'Цифровой паспорт навыков',
    text: 'Профиль фиксирует активность, навыки и подтверждённые результаты.',
  },
  {
    title: 'Аналитика преподавателя',
    text: 'Преподаватель видит прогресс, попытки и динамику обучения.',
  },
  {
    title: 'Карьерный контур',
    text: 'Вакансии и профили связывают обучение с поиском кандидатов.',
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

const heroActions = computed(() => {
  if (!authStore.isAuthenticated) {
    return [
      { to: '/courses', label: 'Смотреть курсы', variant: 'primary' },
      { to: '/login', label: 'Войти / Регистрация', variant: 'secondary' },
    ]
  }

  if (authStore.isTeacher) {
    return [
      { to: '/teacher', label: 'Кабинет автора', variant: 'primary' },
      { to: '/teacher/analytics', label: 'Аналитика', variant: 'secondary' },
    ]
  }

  if (authStore.isEmployer) {
    return [
      { to: '/vacancies', label: 'Вакансии', variant: 'primary' },
      { to: '/employer', label: 'Кандидаты', variant: 'secondary' },
    ]
  }

  return [
    { to: '/courses', label: 'Продолжить обучение', variant: 'primary' },
    { to: '/vacancies', label: 'Вакансии', variant: 'secondary' },
  ]
})

const finalActions = computed(() => {
  if (!authStore.isAuthenticated) {
    return [
      { to: '/courses', label: 'Смотреть курсы', variant: 'primary' },
      { to: '/login', label: 'Войти / Регистрация', variant: 'secondary' },
    ]
  }

  if (authStore.isTeacher) {
    return [
      { to: '/teacher', label: 'Перейти в кабинет', variant: 'primary' },
      { to: '/teacher/analytics', label: 'Открыть аналитику', variant: 'secondary' },
    ]
  }

  if (authStore.isEmployer) {
    return [
      { to: '/vacancies', label: 'Открыть вакансии', variant: 'primary' },
      { to: '/employer', label: 'Найти кандидатов', variant: 'secondary' },
    ]
  }

  return [
    { to: '/courses', label: 'Мои курсы', variant: 'primary' },
    { to: '/vacancies', label: 'Открыть вакансии', variant: 'secondary' },
  ]
})

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
  <div class="mx-auto max-w-[1140px] px-4 pb-14 sm:px-6 lg:px-8 lg:pb-16">
<section class="relative overflow-hidden rounded-[1.5rem] border border-slate-800 bg-slate-900/70 shadow-[0_20px_64px_rgba(2,6,23,0.18)] sm:rounded-[1.85rem] shadow-[inset_0px_0px_5px_1px_rgba(0,0,0,0)] shadow-black/100">
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,rgba(99,102,241,0.22),transparent_34%),radial-gradient(circle_at_82%_16%,rgba(20,184,166,0.16),transparent_30%)]"></div>
  
  <div class="relative grid gap-5 px-4 py-4 sm:px-6 sm:py-5 lg:grid-cols-[1.06fr,0.94fr] lg:gap-5 lg:px-7 lg:py-5 xl:px-8 xl:py-6 items-center">
    
    <div class="min-w-0 flex flex-col justify-center">
      <div>
        <div class="inline-flex w-fit items-center rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.22em] text-indigo-200 sm:text-[11px]">
          Платформа профессионального обучения
        </div>
        
        <h1 class="mt-3 max-w-3xl break-words text-3xl font-black leading-[0.98] text-white sm:text-4xl lg:max-w-[34rem] lg:text-[2.48rem] xl:max-w-[37rem] xl:text-[2.74rem]">
          ElCourse объединяет обучение, проверку знаний и карьерный рост.
        </h1>
        <p class="mt-2.5 max-w-2xl text-sm leading-6 text-slate-300 sm:text-base lg:max-w-[32rem] lg:text-[0.92rem] lg:leading-[1.45rem] xl:max-w-[34rem]">
          Платформа помогает преподавателям создавать курсы, студентам подтверждать навыки, а работодателям находить подходящих кандидатов.
        </p>
      </div>

    

      <div class="mt-4 grid gap-2.5 sm:flex sm:flex-wrap ">
        <RouterLink
          v-for="action in heroActions"
          :key="action.label"
          :to="action.to"
          class="inline-flex items-center justify-center rounded-xl px-[1.125rem] py-2.5 text-center text-sm font-bold transition lg:px-5 lg:py-[0.5625rem]"
          :class="action.variant === 'primary'
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500'
            : 'border border-slate-700 bg-slate-950/30 text-slate-100 hover:border-slate-500 hover:bg-slate-900'"
        >
          {{ action.label }}
        </RouterLink>
      </div>
    </div>

    <div class="relative w-full lg:ml-auto lg:max-w-[30rem] xl:max-w-[31.75rem] ">
      <div class="pointer-events-none absolute inset-6 rounded-full bg-indigo-500/10 blur-3xl "></div>
      
      <div class="relative w-full rounded-[1.25rem] border border-slate-800 bg-slate-950/35 backdrop-blur pt-3 pb-1.5 sm:pt-4 sm:pb-2 lg:pt-3 lg:pb-1.5 p-2aspect-square ">
        <div class="relative w-full h-full overflow-hidden rounded-[1rem]">
          <HeroAnimation />
        </div>
      </div>
    </div>

  </div>
</section>
<section class="mt-5 grid gap-3 lg:grid-cols-3 lg:gap-3.5">
  <article
    v-for="role in roleCards"
    :key="role.title"
    class="group relative rounded-[1.25rem] border border-slate-800/50 bg-slate-900/30 p-4 transition-all duration-500 hover:border-slate-600 hover:bg-slate-800/30"
  >
    <div class="absolute inset-0 rounded-[1.25rem] bg-gradient-to-b from-white/[0.02] to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"></div>

    <div class="flex items-center justify-between relative z-10">
      <h2 class="text-[17px] font-bold text-slate-200 tracking-tight transition-colors group-hover:text-white">
        {{ role.title }}
      </h2>
    </div>

    <p class="mt-2 text-[13px] leading-[1.4] text-slate-500 transition-colors duration-500 group-hover:text-slate-300 relative z-10">
      {{ role.text }}
    </p>

    <div class="absolute top-0 left-1/2 -translate-x-1/2 h-[1px] w-0 bg-gradient-to-r from-transparent via-slate-400 to-transparent transition-all duration-700 group-hover:w-full"></div>

    <div class="absolute inset-0 rounded-[1.25rem] ring-1 ring-inset ring-white/5 opacity-100 pointer-events-none"></div>
  </article>
</section>

<section class="relative mt-5 overflow-hidden rounded-[1.55rem] border border-white/10 bg-slate-900/30 p-5 sm:p-6 lg:p-6 backdrop-blur-md shadow-[inset_0px_0px_5px_1px_rgba(0,0,0,0)] shadow-black/100">
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.08),transparent_40%),radial-gradient(circle_at_80%_80%,rgba(20,184,166,0.05),transparent_40%)] pointer-events-none"></div>

  <div class="max-w-3xl relative z-10">
    <p class="inline-block px-3 py-1 rounded-full border border-white/10 bg-white/5 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
      Возможности
    </p>
    <h2 class="mt-3 text-xl font-black text-white sm:text-[1.65rem] tracking-tight">
      Основные возможности <span class="text-slate-400/60">платформы</span>
    </h2>
  </div>

  <div class="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3 relative z-10">
    <article
      v-for="advantage in advantages"
      :key="advantage.title"
    
      class="group relative overflow-hidden rounded-[1.1rem] border border-white/[0.06] bg-black/[0.08] p-5 transition-all duration-500 hover:border-white/20 hover:bg-white/[0.06]"
    >
      <div class="absolute top-0 left-1/2 -translate-x-1/2 h-[1px] w-0 bg-gradient-to-r from-transparent via-white/30 to-transparent transition-all duration-700 group-hover:w-full"></div>

      <div class="mb-4 relative h-1 w-12 overflow-hidden rounded-full bg-white/10">
        <div class="absolute inset-y-0 left-0 w-full -translate-x-full bg-gradient-to-r from-transparent via-slate-200 to-transparent transition-transform duration-700 ease-in-out group-hover:translate-x-full"></div>
      </div>

      <div class="flex items-center gap-2 mb-3">
        <h3 class="text-[15px] font-bold text-slate-200 transition-colors group-hover:text-white">
          {{ advantage.title }}
        </h3>
        <svg class="h-4 w-4 text-slate-400 opacity-0 -translate-y-2 transition-all duration-300 group-hover:opacity-100 group-hover:translate-y-0" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L1 7L12 12L21 8.05V13.5H23V7L12 2Z"/>
          <path d="M5 11.2V14.6C5 14.6 6.5 17 12 17C17.5 17 19 14.6 19 14.6V11.2L12 14.3125L5 11.2Z" opacity="0.4"/>
        </svg>
      </div>

      <p class="text-[13px] leading-relaxed text-slate-500 group-hover:text-slate-400 transition-colors">
        {{ advantage.text }}
      </p>
    </article>
  </div>
</section>
<section class="mt-5 overflow-hidden rounded-[1.55rem] border border-slate-800 bg-slate-950 p-5 text-center sm:p-7 lg:p-7">
      <p class="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Начните работу</p>
      <h2 class="mx-auto mt-2.5 max-w-3xl text-xl font-black leading-tight text-white sm:text-3xl lg:text-[1.85rem]">
        Объедините обучение, проверку результатов и карьерные сценарии в одной системе.
      </h2>
      <p class="mx-auto mt-2.5 max-w-2xl text-sm leading-[1.375rem] text-slate-400">
        ElCourse подходит для курсов, тестов, подтверждённых навыков и работы с образовательным профилем.
      </p>
      <div class="mt-5 grid gap-2.5 sm:flex sm:flex-wrap sm:justify-center">
        <RouterLink
          v-for="action in finalActions"
          :key="action.label"
          :to="action.to"
          class="inline-flex items-center justify-center rounded-xl px-[1.125rem] py-2.5 text-sm font-bold transition lg:px-5"
          :class="action.variant === 'primary'
            ? 'bg-indigo-600 text-white hover:bg-indigo-500'
            : 'border border-slate-700 text-slate-200 hover:border-slate-500 hover:text-white'"
        >
          {{ action.label }}
        </RouterLink>
      </div>
</section>
  </div>
</template>
