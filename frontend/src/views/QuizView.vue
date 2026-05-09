<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { showError } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const questions = ref([])
const answers = ref({})
const loading = ref(true)
const result = ref(null)
const submitting = ref(false)
const pageError = ref('')

const answeredCount = computed(() => Object.keys(answers.value).length)
const totalQuestions = computed(() => questions.value.length)
const progressPercent = computed(() => {
  if (!totalQuestions.value) return 0
  return Math.round((answeredCount.value / totalQuestions.value) * 100)
})
const allAnswered = computed(() => totalQuestions.value > 0 && answeredCount.value === totalQuestions.value)

const loadQuiz = async () => {
  loading.value = true
  pageError.value = ''
  try {
    const response = await api.get(`/courses/${route.params.id}/quiz/`)
    questions.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки теста:', error)
    pageError.value = 'Не удалось загрузить тест по курсу.'
  } finally {
    loading.value = false
  }
}

const submitQuiz = async () => {
  if (!allAnswered.value) {
    showError('Ответьте на все вопросы перед проверкой.')
    return
  }

  submitting.value = true
  try {
    const response = await api.post(`/courses/${route.params.id}/quiz/check/`, { answers: answers.value })
    result.value = response.data
  } catch (error) {
    showError(error.response?.data?.error || 'Не удалось отправить тест. Попробуйте ещё раз.')
  } finally {
    submitting.value = false
  }
}

const resetQuiz = () => {
  result.value = null
  answers.value = {}
}

onMounted(loadQuiz)
</script>

<template>
  <div class="mx-auto mt-8 max-w-4xl px-4 pb-12">
    <button
      class="mb-5 inline-flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-900/70 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-indigo-400/60 hover:text-white"
      @click="router.back()"
    >
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      Назад
    </button>

    <header class="mb-6 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/20">
      <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300/80">Итоговое тестирование</p>
      <h1 class="mt-2 text-3xl font-black text-slate-100 sm:text-4xl">Проверка знаний по курсу</h1>
      <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
        Ответьте на вопросы и отправьте тест на проверку. Этот экран используется для старого формата курсов; новые тесты открываются внутри прохождения уроков.
      </p>
    </header>

    <div v-if="loading" class="rounded-3xl border border-slate-800 bg-slate-900/60 p-10 text-center text-slate-400">
      <div class="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-400"></div>
      <p class="mt-4 text-sm font-medium">Загрузка вопросов...</p>
    </div>

    <div v-else-if="pageError" class="rounded-3xl border border-rose-500/20 bg-rose-500/10 p-8 text-center text-rose-300">
      {{ pageError }}
    </div>

    <div v-else-if="!result" class="space-y-5">
      <div class="rounded-3xl border border-slate-800 bg-slate-900/60 p-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-sm font-bold text-slate-200">Прогресс ответов</p>
            <p class="text-sm text-slate-500">Заполнено {{ answeredCount }} из {{ totalQuestions }} вопросов.</p>
          </div>
          <span class="rounded-xl border border-indigo-400/25 bg-indigo-500/10 px-3 py-2 text-sm font-black text-indigo-200">
            {{ progressPercent }}%
          </span>
        </div>
        <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-950">
          <div class="h-full rounded-full bg-indigo-500 transition-all duration-300" :style="{ width: `${progressPercent}%` }"></div>
        </div>
      </div>

      <div
        v-for="(q, index) in questions"
        :key="q.id"
        class="rounded-3xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl shadow-slate-950/10"
      >
        <p class="text-xs font-bold uppercase tracking-[0.24em] text-indigo-300">Вопрос {{ index + 1 }}</p>
        <h3 class="mt-2 text-lg font-black leading-relaxed text-slate-100">{{ q.text }}</h3>

        <div class="mt-5 grid gap-2">
          <label
            v-for="choice in q.choices"
            :key="choice.id"
            class="group flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition"
            :class="answers[q.id] === choice.id
              ? 'border-indigo-400/70 bg-indigo-500/15 text-slate-100'
              : 'border-slate-800 bg-slate-950/30 text-slate-300 hover:border-slate-600 hover:bg-slate-900/70'"
          >
            <input v-model="answers[q.id]" type="radio" :name="`q-${q.id}`" :value="choice.id" class="sr-only">
            <span
              class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition"
              :class="answers[q.id] === choice.id
                ? 'border-indigo-300 bg-indigo-500 text-white'
                : 'border-slate-600 bg-slate-950 text-transparent group-hover:border-slate-400'"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span class="text-sm font-medium leading-relaxed">{{ choice.text }}</span>
          </label>
        </div>
      </div>

      <div class="sticky bottom-4 rounded-3xl border border-slate-800 bg-slate-950/90 p-4 shadow-2xl shadow-slate-950/40 backdrop-blur">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-slate-500">
            <span v-if="allAnswered">Все вопросы заполнены.</span>
            <span v-else>Осталось ответить: {{ totalQuestions - answeredCount }}</span>
          </p>
          <button
            class="inline-flex items-center justify-center gap-2 rounded-2xl px-7 py-3 text-sm font-black text-white transition disabled:cursor-not-allowed disabled:opacity-50"
            :class="allAnswered ? 'bg-indigo-600 shadow-lg shadow-indigo-600/20 hover:bg-indigo-500' : 'bg-slate-700'"
            :disabled="!allAnswered || submitting"
            @click="submitQuiz"
          >
            <span v-if="submitting" class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
            <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            {{ submitting ? 'Проверяем...' : 'Завершить и проверить' }}
          </button>
        </div>
      </div>
    </div>

    <section v-else class="rounded-3xl border p-8 text-center shadow-2xl" :class="result.is_passed ? 'border-emerald-400/30 bg-emerald-500/10' : 'border-rose-400/30 bg-rose-500/10'">
      <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl border" :class="result.is_passed ? 'border-emerald-400/30 bg-emerald-500/15 text-emerald-200' : 'border-rose-400/30 bg-rose-500/15 text-rose-200'">
        <svg v-if="result.is_passed" class="h-8 w-8" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else class="h-8 w-8" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        </svg>
      </div>

      <h2 class="text-3xl font-black" :class="result.is_passed ? 'text-emerald-200' : 'text-rose-200'">
        {{ result.is_passed ? 'Тест пройден' : 'Тест не пройден' }}
      </h2>
      <p class="mx-auto mt-3 max-w-xl text-base leading-7 text-slate-300">
        Правильных ответов: {{ result.correct_count }} из {{ result.total_count }}.
        <span v-if="result.is_passed">Навыки могут быть добавлены в цифровой профиль после фиксации результата.</span>
        <span v-else>Повторите материал курса и попробуйте пройти тест ещё раз.</span>
      </p>

      <div class="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
        <RouterLink
          v-if="result.is_passed"
          to="/profile"
          class="inline-flex items-center justify-center rounded-2xl bg-emerald-600 px-7 py-3 text-sm font-black text-white transition hover:bg-emerald-500"
        >
          Открыть профиль
        </RouterLink>
        <button
          v-else
          class="inline-flex items-center justify-center rounded-2xl bg-slate-800 px-7 py-3 text-sm font-black text-white transition hover:bg-slate-700"
          @click="resetQuiz"
        >
          Пройти ещё раз
        </button>
        <RouterLink
          :to="{ name: 'course-detail', params: { id: route.params.id } }"
          class="inline-flex items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/40 px-7 py-3 text-sm font-black text-slate-300 transition hover:border-indigo-400/60 hover:text-white"
        >
          К описанию курса
        </RouterLink>
      </div>
    </section>
  </div>
</template>
