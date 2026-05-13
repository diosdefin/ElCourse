<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  value: {
    type: Object,
    default: () => ({
      passing_score_percentage: 80,
      max_attempts: 3,
      penalty_hours: 24,
      time_limit_minutes: 0,
    }),
  },
})

const emit = defineEmits(['close', 'save'])

const form = reactive({
  passing_score_percentage: 80,
  max_attempts: 3,
  penalty_hours: 24,
  hasTimeLimit: false,
  time_limit_minutes: 0,
})

const normalizedScore = computed(() => Math.min(100, Math.max(0, Number(form.passing_score_percentage) || 0)))
const normalizedAttempts = computed(() => Math.min(10, Math.max(1, Number(form.max_attempts) || 1)))
const normalizedPenalty = computed(() => Math.min(168, Math.max(0, Number(form.penalty_hours) || 0)))
const normalizedTimeLimit = computed(() => (form.hasTimeLimit ? Math.max(1, Number(form.time_limit_minutes) || 1) : 0))

const scoreLevel = computed(() => {
  if (normalizedScore.value >= 85) return { label: 'строгий контроль', tone: 'text-rose-200 border-rose-400/30 bg-rose-400/10' }
  if (normalizedScore.value >= 70) return { label: 'стандартный уровень', tone: 'text-emerald-200 border-emerald-400/30 bg-emerald-400/10' }
  return { label: 'мягкий порог', tone: 'text-amber-200 border-amber-400/30 bg-amber-400/10' }
})

watch(
  () => [props.open, props.value],
  () => {
    if (!props.open) return

    const value = props.value || {}
    form.passing_score_percentage = Number(value.passing_score_percentage ?? 80)
    form.max_attempts = Number(value.max_attempts ?? 3)
    form.penalty_hours = Number(value.penalty_hours ?? 24)
    form.time_limit_minutes = Number(value.time_limit_minutes ?? 0)
    form.hasTimeLimit = Number(value.time_limit_minutes ?? 0) > 0
  },
  { immediate: true, deep: true }
)

const setScore = (score) => {
  form.passing_score_percentage = score
}

const handleClose = () => {
  emit('close')
}

const handleSave = () => {
  emit('save', {
    passing_score_percentage: normalizedScore.value,
    max_attempts: normalizedAttempts.value,
    penalty_hours: normalizedPenalty.value,
    time_limit_minutes: normalizedTimeLimit.value,
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4"
    @mousedown.self="handleClose">
    <section
      class="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950/40">
      <header class="sticky top-0 z-10 border-b border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:px-6 sm:py-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.24em] text-indigo-300">Параметры прохождения</p>
            <h3 class="mt-1 text-xl font-black text-white sm:text-2xl">Настройки теста</h3>
            <p class="mt-1 text-sm text-slate-400">Эти правила применяются к попыткам, проходному баллу и таймеру.</p>
          </div>
          <button type="button"
            class="group relative grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-700 bg-slate-950 text-slate-300 transition hover:border-slate-500 hover:text-white"
            @click="handleClose">
            <span class="sr-only">Закрыть окно</span>
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
        <div class="grid gap-4 sm:grid-cols-3">
          <article class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Проходной балл</p>
            <p class="mt-2 text-3xl font-black text-white">{{ normalizedScore }}%</p>
          </article>
          <article class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Попытки</p>
            <p class="mt-2 text-3xl font-black text-white">{{ normalizedAttempts }}</p>
          </article>
          <article class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Лимит времени</p>
            <p class="mt-2 text-3xl font-black text-white">{{ normalizedTimeLimit || 'Нет' }}</p>
          </article>
        </div>

        <div class="mt-6 space-y-5">
          <section class="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <label class="text-sm font-bold text-slate-100">Проходной балл</label>
                <p class="mt-1 text-xs text-slate-500">Минимальный процент правильных ответов для успешной сдачи.</p>
              </div>
              <span class="rounded-full border px-3 py-1 text-xs font-bold" :class="scoreLevel.tone">{{ scoreLevel.label
                }}</span>
            </div>

            <input v-model.number="form.passing_score_percentage" type="range" min="0" max="100" step="1"
              class="mt-5 w-full accent-indigo-500">

            <div class="mt-4 flex flex-wrap gap-2">
              <button v-for="score in [60, 70, 80, 90]" :key="score" type="button"
                class="rounded-xl border px-3 py-2 text-xs font-bold transition"
                :class="normalizedScore === score ? 'border-indigo-400 bg-indigo-500/15 text-indigo-100' : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500 hover:text-white'"
                @click="setScore(score)">
                {{ score }}%
              </button>
            </div>
          </section>

          <section class="grid gap-4 md:grid-cols-2">
            <div class="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
              <label class="text-sm font-bold text-slate-100">Максимум попыток</label>
              <p class="mt-1 text-xs text-slate-500">От 1 до 10. После исчерпания попыток включается штрафная пауза.</p>
              <input v-model.number="form.max_attempts" type="number" min="1" max="10"
                class="mt-3 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-400">
            </div>

            <div class="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
              <label class="text-sm font-bold text-slate-100">Штрафные часы</label>
              <p class="mt-1 text-xs text-slate-500">От 0 до 168. Значение 0 отключает блокировку после попыток.</p>
              <input v-model.number="form.penalty_hours" type="number" min="0" max="168"
                class="mt-3 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-400">
            </div>
          </section>

          <section class="rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
            <div class="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h4 class="text-sm font-bold text-slate-100">Ограничение по времени</h4>
                <p class="mt-1 text-xs text-slate-500">Если выключено, студент проходит тест без таймера.</p>
              </div>

              <label class="relative inline-flex cursor-pointer items-center">
                <input v-model="form.hasTimeLimit" type="checkbox" class="peer sr-only">
                <span
                  class="h-7 w-12 rounded-full border border-slate-700 bg-slate-800 transition peer-checked:border-indigo-400 peer-checked:bg-indigo-600"></span>
                <span
                  class="absolute left-1 h-5 w-5 rounded-full bg-slate-300 transition peer-checked:translate-x-5 peer-checked:bg-white"></span>
              </label>
            </div>

            <div v-if="form.hasTimeLimit" class="mt-4">
              <label class="text-xs font-semibold text-slate-400">Лимит в минутах</label>
              <input v-model.number="form.time_limit_minutes" type="number" min="1" max="240"
                class="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-400"
                placeholder="Например, 30">
            </div>
          </section>
        </div>
      </div>

      <footer class="sticky bottom-0 z-10 border-t border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:px-6">
        <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button"
            class="rounded-xl border border-slate-700 bg-slate-950 px-5 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
            @click="handleClose">
            Отмена
          </button>
          <button type="button"
            class="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500"
            @click="handleSave">
            Сохранить настройки
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
