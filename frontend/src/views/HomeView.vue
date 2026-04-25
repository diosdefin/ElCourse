<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const courses = ref([])
const loading = ref(true)

const featureCards = [
  {
    title: 'Геймификация обучения',
    description: 'Прогресс по навыкам, heatmap активности и цифровой профиль превращают каждый курс в видимый карьерный рост.',
    accent: 'from-indigo-500/30 via-indigo-500/10 to-transparent',
  },
  {
    title: 'Сертификация навыков',
    description: 'Навыки закрепляются только после Quiz, поэтому профиль показывает не обещания, а реальные подтвержденные результаты.',
    accent: 'from-emerald-500/30 via-emerald-500/10 to-transparent',
  },
  {
    title: 'Поиск талантов',
    description: 'Работодатели открывают публичные профили, смотрят развитие и отправляют офферы без дублей и хаоса.',
    accent: 'from-sky-500/30 via-sky-500/10 to-transparent',
  },
]

const floatingHighlights = [
  'Heatmap активности',
  'Skill Passport',
  'Работодательский поиск',
  'Quiz-driven skills',
]

const featuredCourses = computed(() => courses.value.slice(0, 3))
const courseCount = computed(() => courses.value.length)
const skillCount = computed(() => {
  const uniqueSkills = new Set()
  for (const course of courses.value) {
    for (const skill of course.skills_covered || []) {
      uniqueSkills.add(skill.name)
    }
  }
  return uniqueSkills.size
})

onMounted(async () => {
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/courses/')
    courses.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-10 pb-12">
    <section class="relative overflow-hidden rounded-[2.5rem] border border-slate-800/80 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900 via-slate-900 to-slate-900 px-6 py-12 shadow-[0_40px_120px_rgba(2,6,23,0.55)] sm:px-10 lg:px-14">
      <div class="pointer-events-none absolute inset-0">
        <div class="float-slow absolute left-[8%] top-16 h-24 w-24 rounded-full bg-indigo-500/20 blur-2xl"></div>
        <div class="float-medium absolute right-[14%] top-24 h-20 w-20 rounded-full bg-emerald-400/15 blur-2xl"></div>
        <div class="float-fast absolute bottom-16 left-[28%] h-28 w-28 rounded-full bg-sky-400/10 blur-3xl"></div>
        <div class="absolute -right-16 -top-12 h-72 w-72 rounded-full bg-indigo-500/10 blur-3xl"></div>
      </div>

      <div class="relative grid gap-10 lg:grid-cols-[1.15fr,0.85fr] lg:items-center">
        <div class="max-w-3xl">
          <span class="inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-500/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.35em] text-indigo-200">
            ELCOURSE PLATFORM
          </span>
          <h1 class="mt-6 text-4xl font-black leading-tight text-white sm:text-5xl lg:text-6xl">
            Учитесь, прокачивайте профиль и становитесь заметными для сильных команд.
          </h1>
          <p class="mt-5 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
            Платформа соединяет курсы, подтвержденные навыки, публичные профили и поиск талантов в одну аккуратную карьерную витрину.
          </p>

          <div class="mt-8 flex flex-wrap gap-3">
            <RouterLink
              :to="authStore.isAuthenticated ? '/profile' : '/login'"
              class="rounded-full bg-white px-6 py-3 text-sm font-bold text-slate-950 transition hover:bg-slate-100"
            >
              {{ authStore.isAuthenticated ? 'Открыть мой профиль' : 'Зарегистрироваться' }}
            </RouterLink>
            <RouterLink
              to="/community"
              class="rounded-full border border-slate-700 bg-slate-950/30 px-6 py-3 text-sm font-bold text-slate-100 transition hover:border-slate-500 hover:bg-slate-900/60"
            >
              Посмотреть комьюнити
            </RouterLink>
          </div>

          <div class="mt-10 grid gap-3 sm:grid-cols-3">
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 backdrop-blur">
              <p class="text-xs uppercase tracking-[0.28em] text-slate-500">Курсы</p>
              <p class="mt-2 text-3xl font-black text-white">{{ courseCount }}</p>
            </div>
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 backdrop-blur">
              <p class="text-xs uppercase tracking-[0.28em] text-slate-500">Навыки</p>
              <p class="mt-2 text-3xl font-black text-white">{{ skillCount }}</p>
            </div>
            <div class="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 backdrop-blur">
              <p class="text-xs uppercase tracking-[0.28em] text-slate-500">Сценарии</p>
              <p class="mt-2 text-3xl font-black text-white">3 в 1</p>
            </div>
          </div>
        </div>

        <div class="relative">
          <div class="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-indigo-500/15 via-transparent to-emerald-400/10 blur-2xl"></div>
          <div class="relative rounded-[2rem] border border-slate-800/80 bg-slate-950/50 p-6 shadow-2xl backdrop-blur-xl">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Витрина роста</p>
                <p class="mt-2 text-2xl font-black text-white">Из уроков в офферы</p>
              </div>
              <div class="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">
                live
              </div>
            </div>

            <div class="mt-6 grid gap-4">
              <div
                v-for="(item, index) in floatingHighlights"
                :key="item"
                class="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"
                :class="index % 2 === 0 ? 'float-slow' : 'float-medium'"
              >
                <p class="text-sm font-semibold text-slate-200">{{ item }}</p>
                <p class="mt-1 text-xs leading-5 text-slate-500">
                  {{ index === 0 ? 'Каждый учебный день превращается в видимую историю прогресса.' : index === 1 ? 'Подтвержденные навыки и обучение в процессе живут в одном профиле.' : index === 2 ? 'Работодатели быстро находят нужных людей и не дублируют офферы.' : 'Навыки выдаются после реальной проверки, а не по кнопке.' }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-5 lg:grid-cols-3">
      <article
        v-for="feature in featureCards"
        :key="feature.title"
        class="group relative overflow-hidden rounded-[1.8rem] border border-slate-800/70 bg-slate-900/70 p-6 transition duration-300 hover:-translate-y-1.5 hover:border-slate-600 hover:shadow-[0_30px_80px_rgba(15,23,42,0.45)]"
      >
        <div class="absolute inset-0 bg-gradient-to-br opacity-0 transition duration-300 group-hover:opacity-100" :class="feature.accent"></div>
        <div class="relative">
          <p class="text-sm font-black uppercase tracking-[0.28em] text-slate-500">Особенность</p>
          <h2 class="mt-4 text-2xl font-black text-white">{{ feature.title }}</h2>
          <p class="mt-4 text-sm leading-7 text-slate-300">{{ feature.description }}</p>
        </div>
      </article>
    </section>

    <section class="rounded-[2rem] border border-slate-800/70 bg-slate-900/60 p-6 shadow-xl shadow-slate-950/20">
      <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Каталог</p>
          <h2 class="mt-3 text-3xl font-black text-white">Стартуйте с программ, которые действительно двигают профиль</h2>
        </div>
        <RouterLink
          to="/community"
          class="inline-flex w-fit items-center gap-2 rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
        >
          Комьюнити и профили
        </RouterLink>
      </div>

      <div v-if="loading" class="mt-8 rounded-[1.5rem] border border-slate-800 bg-slate-950/50 px-6 py-14 text-center text-slate-400">
        Загружаем каталог программ...
      </div>

      <div v-else class="mt-8 grid gap-5 lg:grid-cols-3">
        <article
          v-for="course in featuredCourses"
          :key="course.id"
          class="group overflow-hidden rounded-[1.6rem] border border-slate-800 bg-slate-950/40"
        >
          <div class="relative h-40 overflow-hidden border-b border-slate-800 bg-slate-900">
            <div
              v-if="course.image"
              class="absolute inset-0 bg-cover bg-center opacity-75 transition duration-500 group-hover:scale-105"
              :style="`background-image: url(${course.image})`"
            ></div>
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-900/20 to-transparent"></div>
            <div class="absolute bottom-4 left-4 right-4 flex flex-wrap gap-2">
              <span
                v-for="skill in (course.skills_covered || []).slice(0, 3)"
                :key="skill.id"
                class="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold text-white backdrop-blur"
              >
                {{ skill.name }}
              </span>
            </div>
          </div>

          <div class="p-5">
            <h3 class="text-xl font-black text-white">{{ course.title }}</h3>
            <p class="mt-3 line-clamp-3 text-sm leading-6 text-slate-400">{{ course.description }}</p>
            <div class="mt-5 flex items-center justify-between text-xs uppercase tracking-[0.22em] text-slate-500">
              <span>Автор</span>
              <span>{{ course.author_name }}</span>
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

    <section class="relative overflow-hidden rounded-[2rem] border border-slate-800/70 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 px-6 py-10 text-center shadow-xl shadow-slate-950/30">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_30%),radial-gradient(circle_at_bottom,_rgba(16,185,129,0.12),_transparent_35%)]"></div>
      <div class="relative mx-auto max-w-3xl">
        <p class="text-xs font-bold uppercase tracking-[0.35em] text-slate-500">Начните сегодня</p>
        <h2 class="mt-4 text-3xl font-black text-white sm:text-4xl">
          Зарегистрируйтесь и превратите обучение в портфолио, которое видно с первого взгляда.
        </h2>
        <p class="mt-4 text-sm leading-7 text-slate-400 sm:text-base">
          Курсы, активность, навыки, друзья и поиск талантов собираются в одну систему, где ваш прогресс читается без лишних объяснений.
        </p>
        <div class="mt-8 flex flex-wrap justify-center gap-3">
          <RouterLink
            :to="authStore.isAuthenticated ? '/profile' : '/login'"
            class="rounded-full bg-indigo-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-indigo-500"
          >
            {{ authStore.isAuthenticated ? 'Продолжить путь' : 'Создать аккаунт' }}
          </RouterLink>
          <RouterLink
            to="/community"
            class="rounded-full border border-slate-700 px-6 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
          >
            Изучить сообщество
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.float-slow {
  animation: float 8s ease-in-out infinite;
}

.float-medium {
  animation: float 6.5s ease-in-out infinite;
}

.float-fast {
  animation: float 5.5s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px);
  }

  50% {
    transform: translateY(-10px);
  }
}
</style>
