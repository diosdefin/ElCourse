<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'

const route = useRoute()
const router = useRouter()

const QUESTION_LIMIT = 1000
const CHOICE_LIMIT = 500
const EXPLANATION_LIMIT = 2000
const MIN_CHOICES = 2
const MAX_CHOICES = 8

const questions = ref([])
const isLoading = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const searchQuery = ref('')
const filterMode = ref('all')
const editingQuestionId = ref(null)

const draft = reactive({
  text: '',
  is_multiple: false,
  explanation: '',
  choices: [
    { text: '', is_correct: true },
    { text: '', is_correct: false },
    { text: '', is_correct: false },
  ],
})

const editDraft = reactive({
  text: '',
  is_multiple: false,
  explanation: '',
  choices: [],
})

const confirmDialog = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  pending: false,
  action: null,
})

const courseId = computed(() => route.params.id)

const normalizeQuestion = (question) => {
  const choices = Array.isArray(question?.choices) ? question.choices : []
  const correctCount = choices.filter((choice) => choice.is_correct).length

  return {
    ...question,
    text: question?.text || '',
    explanation: question?.explanation || '',
    is_multiple: Boolean(question?.is_multiple ?? correctCount > 1),
    choices: choices.map((choice) => ({
      id: choice.id,
      text: choice.text || '',
      is_correct: Boolean(choice.is_correct),
    })),
  }
}

const fetchQuiz = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await api.get(`/teacher/courses/${courseId.value}/quiz-editor/`)
    const list = Array.isArray(response.data) ? response.data : response.data?.questions || []
    questions.value = list.map(normalizeQuestion)
  } catch (error) {
    console.error(error)
    errorMessage.value = 'Не удалось загрузить вопросы теста.'
  } finally {
    isLoading.value = false
  }
}

const questionStats = computed(() => {
  const total = questions.value.length
  const multi = questions.value.filter((question) => question.is_multiple).length
  const single = total - multi
  const averageChoices = total
    ? Math.round(questions.value.reduce((sum, question) => sum + question.choices.length, 0) / total)
    : 0

  return { total, single, multi, averageChoices }
})

const filteredQuestions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return questions.value.filter((question) => {
    const matchesQuery = !query || question.text.toLowerCase().includes(query) || question.choices.some((choice) => choice.text.toLowerCase().includes(query))
    const matchesMode = filterMode.value === 'all' || (filterMode.value === 'single' && !question.is_multiple) || (filterMode.value === 'multiple' && question.is_multiple)
    return matchesQuery && matchesMode
  })
})

const autoGrowElement = (element) => {
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 260)}px`
}

const autoGrowTextarea = (event) => {
  autoGrowElement(event.target)
}

const clearMessages = () => {
  errorMessage.value = ''
  successMessage.value = ''
}

const resetDraft = () => {
  draft.text = ''
  draft.is_multiple = false
  draft.explanation = ''
  draft.choices = [
    { text: '', is_correct: true },
    { text: '', is_correct: false },
    { text: '', is_correct: false },
  ]
}

const normalizeSingleCorrect = (source) => {
  const correctIndex = source.choices.findIndex((choice) => choice.is_correct)
  source.choices.forEach((choice, index) => {
    choice.is_correct = index === (correctIndex >= 0 ? correctIndex : 0)
  })
}

watch(
  () => draft.is_multiple,
  (isMultiple) => {
    if (!isMultiple) normalizeSingleCorrect(draft)
  }
)

watch(
  () => editDraft.is_multiple,
  (isMultiple) => {
    if (!isMultiple && editDraft.choices.length) normalizeSingleCorrect(editDraft)
  }
)

const setCorrect = (source, index) => {
  if (source.is_multiple) {
    source.choices[index].is_correct = !source.choices[index].is_correct
    return
  }

  source.choices.forEach((choice, choiceIndex) => {
    choice.is_correct = choiceIndex === index
  })
}

const addChoice = (source) => {
  clearMessages()
  if (source.choices.length >= MAX_CHOICES) {
    errorMessage.value = `Для одного вопроса допускается не более ${MAX_CHOICES} вариантов ответа.`
    return
  }

  source.choices.push({ text: '', is_correct: false })
}

const removeChoice = (source, index) => {
  clearMessages()
  if (source.choices.length <= MIN_CHOICES) {
    errorMessage.value = `Оставьте минимум ${MIN_CHOICES} варианта ответа.`
    return
  }

  const wasCorrect = source.choices[index].is_correct
  source.choices.splice(index, 1)

  if (!source.is_multiple && wasCorrect) normalizeSingleCorrect(source)
}

const buildPayload = (source) => ({
  text: source.text.trim(),
  is_multiple: Boolean(source.is_multiple),
  explanation: source.explanation.trim(),
  choices: source.choices
    .map((choice) => ({
      ...(choice.id ? { id: choice.id } : {}),
      text: choice.text.trim(),
      is_correct: Boolean(choice.is_correct),
    }))
    .filter((choice) => choice.text),
})

const validateQuestion = (source) => {
  const payload = buildPayload(source)
  const errors = []

  if (!payload.text) errors.push('Введите текст вопроса.')
  if (payload.text.length > QUESTION_LIMIT) errors.push(`Вопрос не должен превышать ${QUESTION_LIMIT} символов.`)
  if (payload.explanation.length > EXPLANATION_LIMIT) errors.push(`Объяснение не должно превышать ${EXPLANATION_LIMIT} символов.`)
  if (payload.choices.length < MIN_CHOICES) errors.push(`Добавьте минимум ${MIN_CHOICES} варианта ответа.`)
  if (payload.choices.some((choice) => choice.text.length > CHOICE_LIMIT)) errors.push(`Вариант ответа не должен превышать ${CHOICE_LIMIT} символов.`)

  const correctCount = payload.choices.filter((choice) => choice.is_correct).length
  if (!correctCount) errors.push('Отметьте хотя бы один правильный ответ.')
  if (!payload.is_multiple && correctCount > 1) errors.push('Для вопроса с одним ответом оставьте только один правильный вариант.')

  return errors
}

const draftErrors = computed(() => validateQuestion(draft))
const editErrors = computed(() => (editingQuestionId.value ? validateQuestion(editDraft) : []))

const questionTypeLabel = (question) => (question.is_multiple ? 'Несколько ответов' : 'Один ответ')

const correctChoicesCount = (question) => question.choices.filter((choice) => choice.is_correct).length

const saveQuestion = async () => {
  clearMessages()
  const errors = validateQuestion(draft)

  if (errors.length) {
    errorMessage.value = errors[0]
    return
  }

  isSaving.value = true

  try {
    const response = await api.post(`/teacher/courses/${courseId.value}/quiz-editor/`, buildPayload(draft))
    const created = response.data?.id ? normalizeQuestion(response.data) : null

    if (created) {
      questions.value = [created, ...questions.value]
    } else {
      await fetchQuiz()
    }

    resetDraft()
    successMessage.value = 'Вопрос добавлен в базу теста.'
    await nextTick()
    document.querySelectorAll('[data-autogrow]').forEach(autoGrowElement)
  } catch (error) {
    console.error(error)
    errorMessage.value = error?.response?.data?.detail || 'Не удалось добавить вопрос.'
  } finally {
    isSaving.value = false
  }
}

const startEdit = (question) => {
  clearMessages()
  const source = normalizeQuestion(question)
  editingQuestionId.value = source.id
  editDraft.text = source.text
  editDraft.is_multiple = source.is_multiple
  editDraft.explanation = source.explanation
  editDraft.choices = source.choices.map((choice) => ({ ...choice }))

  nextTick(() => {
    document.querySelectorAll('[data-autogrow]').forEach(autoGrowElement)
  })
}

const cancelEdit = () => {
  editingQuestionId.value = null
  editDraft.text = ''
  editDraft.is_multiple = false
  editDraft.explanation = ''
  editDraft.choices = []
}

const requestWithEndpointFallback = async (method, urls, payload) => {
  let lastError = null

  for (const url of urls) {
    try {
      if (method === 'patch') return await api.patch(url, payload)
      if (method === 'delete') return await api.delete(url)
    } catch (error) {
      lastError = error
      const status = error?.response?.status
      if (status && ![404, 405].includes(status)) break
    }
  }

  throw lastError
}

const saveEdit = async (question) => {
  clearMessages()
  const errors = validateQuestion(editDraft)

  if (errors.length) {
    errorMessage.value = errors[0]
    return
  }

  isSaving.value = true

  try {
    const response = await requestWithEndpointFallback('patch', [
      `/teacher/questions/${question.id}/`,
      `/teacher/courses/${courseId.value}/quiz-editor/${question.id}/`,
    ], buildPayload(editDraft))

    const updated = normalizeQuestion(response.data?.id ? response.data : { ...question, ...buildPayload(editDraft), id: question.id })
    questions.value = questions.value.map((item) => (item.id === question.id ? updated : item))
    cancelEdit()
    successMessage.value = 'Вопрос обновлён.'
  } catch (error) {
    console.error(error)
    errorMessage.value = error?.response?.data?.detail || 'Не удалось обновить вопрос. Проверьте, поддерживает ли backend редактирование базы вопросов.'
  } finally {
    isSaving.value = false
  }
}

const openConfirmDialog = ({ title, message, confirmText, action }) => {
  confirmDialog.title = title
  confirmDialog.message = message
  confirmDialog.confirmText = confirmText || 'Удалить'
  confirmDialog.action = action
  confirmDialog.pending = false
  confirmDialog.open = true
}

const closeConfirmDialog = () => {
  if (confirmDialog.pending) return
  confirmDialog.open = false
  confirmDialog.action = null
}

const submitConfirmDialog = async () => {
  if (!confirmDialog.action) return

  confirmDialog.pending = true
  try {
    await confirmDialog.action()
    confirmDialog.open = false
    confirmDialog.action = null
  } finally {
    confirmDialog.pending = false
  }
}

const requestDeleteQuestion = (question) => {
  openConfirmDialog({
    title: 'Удалить вопрос?',
    message: `Вопрос «${question.text.slice(0, 80)}${question.text.length > 80 ? '...' : ''}» будет удалён из базы теста. Это действие нельзя отменить.`,
    confirmText: 'Удалить вопрос',
    action: async () => {
      clearMessages()
      isDeleting.value = true

      try {
        await requestWithEndpointFallback('delete', [
          `/teacher/questions/${question.id}/`,
          `/teacher/courses/${courseId.value}/quiz-editor/${question.id}/`,
        ])

        questions.value = questions.value.filter((item) => item.id !== question.id)
        if (editingQuestionId.value === question.id) cancelEdit()
        successMessage.value = 'Вопрос удалён.'
      } catch (error) {
        console.error(error)
        errorMessage.value = error?.response?.data?.detail || 'Не удалось удалить вопрос. Проверьте, поддерживает ли backend удаление базы вопросов.'
      } finally {
        isDeleting.value = false
      }
    },
  })
}

const copyQuestionToDraft = (question) => {
  clearMessages()
  const source = normalizeQuestion(question)
  draft.text = source.text
  draft.is_multiple = source.is_multiple
  draft.explanation = source.explanation
  draft.choices = source.choices.map((choice) => ({ text: choice.text, is_correct: choice.is_correct }))

  nextTick(() => {
    document.getElementById('question-draft')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    document.querySelectorAll('[data-autogrow]').forEach(autoGrowElement)
  })
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/teacher')
}

onMounted(fetchQuiz)
</script>

<template>
  <main class="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-7xl">
      <header class="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-900/80 shadow-2xl shadow-slate-950/30">
        <div class="border-b border-slate-800 px-6 py-5 sm:px-8">
          <div class="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <button type="button" class="mb-4 inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-slate-500 hover:text-white" @click="goBack">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="m15 18-6-6 6-6" />
                </svg>
                Назад
              </button>
              <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300">Преподавательский контур</p>
              <h1 class="mt-2 text-3xl font-black text-white sm:text-4xl">Редактор вопросов теста</h1>
              <p class="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                Создавайте базу вопросов для проверочных заданий и итогового экзамена. Интерфейс ограничивает длину текстов и помогает не сохранить вопрос без правильного ответа.
              </p>
            </div>

            <button type="button" class="inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isLoading" @click="fetchQuiz">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" />
              </svg>
              Обновить список
            </button>
          </div>
        </div>

        <div class="grid gap-3 px-6 py-5 sm:grid-cols-2 sm:px-8 lg:grid-cols-4">
          <article class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Всего вопросов</p>
            <p class="mt-2 text-3xl font-black text-white">{{ questionStats.total }}</p>
          </article>
          <article class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Один ответ</p>
            <p class="mt-2 text-3xl font-black text-white">{{ questionStats.single }}</p>
          </article>
          <article class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Несколько ответов</p>
            <p class="mt-2 text-3xl font-black text-white">{{ questionStats.multi }}</p>
          </article>
          <article class="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Среднее число вариантов</p>
            <p class="mt-2 text-3xl font-black text-white">{{ questionStats.averageChoices }}</p>
          </article>
        </div>
      </header>

      <div v-if="errorMessage" class="mt-6 rounded-2xl border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="mt-6 rounded-2xl border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
        {{ successMessage }}
      </div>

      <div class="mt-8 grid gap-6 xl:grid-cols-[440px_minmax(0,1fr)]">
        <section id="question-draft" class="h-max rounded-[2rem] border border-slate-800 bg-slate-900/80 p-5 shadow-xl shadow-slate-950/20 sm:p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.24em] text-emerald-300">Новый элемент</p>
              <h2 class="mt-1 text-2xl font-black text-white">Добавить вопрос</h2>
            </div>
            <button type="button" class="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-slate-500 hover:text-white" @click="resetDraft">
              Очистить
            </button>
          </div>

          <div class="mt-6 space-y-5">
            <div>
              <div class="mb-2 flex items-center justify-between gap-3">
                <label class="text-sm font-bold text-slate-200">Текст вопроса</label>
                <span class="text-xs" :class="draft.text.length > QUESTION_LIMIT ? 'text-rose-300' : 'text-slate-500'">{{ draft.text.length }}/{{ QUESTION_LIMIT }}</span>
              </div>
              <textarea
                v-model="draft.text"
                data-autogrow
                rows="3"
                :maxlength="QUESTION_LIMIT"
                class="max-h-64 min-h-[92px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
                placeholder="Например: Какой HTTP-метод используется для частичного обновления ресурса?"
                @input="autoGrowTextarea"
              ></textarea>
            </div>

            <div class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-bold text-slate-200">Тип вопроса</p>
                  <p class="mt-1 text-xs text-slate-500">Выберите, сколько правильных вариантов может быть.</p>
                </div>
                <div class="grid grid-cols-2 rounded-xl border border-slate-700 bg-slate-900 p-1 text-xs font-bold">
                  <button type="button" class="rounded-lg px-3 py-2 transition" :class="!draft.is_multiple ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'" @click="draft.is_multiple = false">
                    Один
                  </button>
                  <button type="button" class="rounded-lg px-3 py-2 transition" :class="draft.is_multiple ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'" @click="draft.is_multiple = true">
                    Несколько
                  </button>
                </div>
              </div>
            </div>

            <div>
              <div class="mb-3 flex items-center justify-between gap-3">
                <label class="text-sm font-bold text-slate-200">Варианты ответа</label>
                <button type="button" class="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-slate-500 hover:text-white" @click="addChoice(draft)">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                  Добавить
                </button>
              </div>

              <div class="space-y-2">
                <div v-for="(choice, index) in draft.choices" :key="index" class="flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-950/70 p-2">
                  <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-xl border transition" :class="choice.is_correct ? 'border-emerald-400 bg-emerald-500/15 text-emerald-100' : 'border-slate-700 bg-slate-900 text-slate-500 hover:text-slate-200'" @click="setCorrect(draft, index)">
                    <span class="sr-only">Отметить правильный вариант</span>
                    <svg v-if="draft.is_multiple" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 5h16v16H4z" /><path v-if="choice.is_correct" d="m8 13 3 3 5-7" /></svg>
                    <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8" /><circle v-if="choice.is_correct" cx="12" cy="12" r="3" fill="currentColor" stroke="none" /></svg>
                  </button>
                  <input v-model="choice.text" :maxlength="CHOICE_LIMIT" type="text" class="min-w-0 flex-1 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400" :placeholder="`Вариант ответа ${index + 1}`">
                  <button type="button" class="group relative grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-rose-500/10 text-rose-200 transition hover:bg-rose-500/20 hover:text-white" @click="removeChoice(draft, index)">
                    <span class="sr-only">Удалить вариант</span>
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
                    <span class="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Удалить</span>
                  </button>
                </div>
              </div>
            </div>

            <div>
              <div class="mb-2 flex items-center justify-between gap-3">
                <label class="text-sm font-bold text-slate-200">Объяснение после проверки</label>
                <span class="text-xs" :class="draft.explanation.length > EXPLANATION_LIMIT ? 'text-rose-300' : 'text-slate-500'">{{ draft.explanation.length }}/{{ EXPLANATION_LIMIT }}</span>
              </div>
              <textarea
                v-model="draft.explanation"
                data-autogrow
                rows="2"
                :maxlength="EXPLANATION_LIMIT"
                class="max-h-56 min-h-[72px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
                placeholder="Кратко объясните правильный ответ. Это поможет студенту разобрать ошибку."
                @input="autoGrowTextarea"
              ></textarea>
            </div>

            <div v-if="draftErrors.length" class="rounded-2xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-xs leading-5 text-amber-100">
              {{ draftErrors[0] }}
            </div>

            <button type="button" class="w-full rounded-2xl bg-emerald-600 px-5 py-4 text-sm font-black text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isSaving || draftErrors.length" @click="saveQuestion">
              {{ isSaving ? 'Сохранение...' : 'Добавить вопрос' }}
            </button>
          </div>
        </section>

        <section class="rounded-[2rem] border border-slate-800 bg-slate-900/80 p-5 shadow-xl shadow-slate-950/20 sm:p-6">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.24em] text-sky-300">База курса</p>
              <h2 class="mt-1 text-2xl font-black text-white">Список вопросов</h2>
              <p class="mt-1 text-sm text-slate-500">Найдено: {{ filteredQuestions.length }} из {{ questions.length }}</p>
            </div>

            <div class="flex flex-col gap-3 sm:flex-row">
              <input v-model.trim="searchQuery" type="search" class="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400 sm:w-72" placeholder="Поиск по вопросу или ответу">
              <select v-model="filterMode" class="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-200 outline-none transition focus:border-indigo-400">
                <option value="all">Все типы</option>
                <option value="single">Один ответ</option>
                <option value="multiple">Несколько ответов</option>
              </select>
            </div>
          </div>

          <div v-if="isLoading" class="mt-6 space-y-3">
            <div v-for="item in 3" :key="item" class="h-36 animate-pulse rounded-2xl border border-slate-800 bg-slate-950/60"></div>
          </div>

          <div v-else-if="!questions.length" class="mt-6 rounded-3xl border border-dashed border-slate-700 bg-slate-950/60 px-6 py-12 text-center">
            <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-slate-700 bg-slate-900 text-slate-400">
              <svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 11h6M9 15h6" /><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v5h5" /></svg>
            </div>
            <h3 class="mt-4 text-lg font-black text-white">Вопросов пока нет</h3>
            <p class="mt-2 text-sm text-slate-500">Добавьте первый вопрос слева, чтобы сформировать базу теста.</p>
          </div>

          <div v-else-if="!filteredQuestions.length" class="mt-6 rounded-3xl border border-dashed border-slate-700 bg-slate-950/60 px-6 py-10 text-center text-sm text-slate-500">
            По выбранному фильтру вопросы не найдены.
          </div>

          <div v-else class="mt-6 space-y-4">
            <article v-for="(question, index) in filteredQuestions" :key="question.id" class="rounded-3xl border border-slate-800 bg-slate-950/70 p-4 transition hover:border-slate-700">
              <template v-if="editingQuestionId === question.id">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <span class="rounded-full border border-indigo-400/30 bg-indigo-400/10 px-3 py-1 text-xs font-bold text-indigo-200">Редактирование</span>
                  <div class="flex gap-2">
                    <button type="button" class="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-300 transition hover:text-white" @click="cancelEdit">Отмена</button>
                    <button type="button" class="rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60" :disabled="isSaving || editErrors.length" @click="saveEdit(question)">
                      Сохранить
                    </button>
                  </div>
                </div>

                <textarea v-model="editDraft.text" data-autogrow rows="3" :maxlength="QUESTION_LIMIT" class="mt-4 max-h-64 min-h-[92px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400" @input="autoGrowTextarea"></textarea>

                <div class="mt-4 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
                  <div class="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
                    <p class="text-xs font-bold text-slate-400">Тип вопроса</p>
                    <div class="mt-3 grid grid-cols-2 rounded-xl border border-slate-700 bg-slate-950 p-1 text-xs font-bold">
                      <button type="button" class="rounded-lg px-3 py-2 transition" :class="!editDraft.is_multiple ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'" @click="editDraft.is_multiple = false">Один</button>
                      <button type="button" class="rounded-lg px-3 py-2 transition" :class="editDraft.is_multiple ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'" @click="editDraft.is_multiple = true">Несколько</button>
                    </div>
                  </div>

                  <div class="space-y-2">
                    <div v-for="(choice, choiceIndex) in editDraft.choices" :key="choice.id || choiceIndex" class="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/70 p-2">
                      <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-xl border transition" :class="choice.is_correct ? 'border-emerald-400 bg-emerald-500/15 text-emerald-100' : 'border-slate-700 bg-slate-950 text-slate-500 hover:text-slate-200'" @click="setCorrect(editDraft, choiceIndex)">
                        <span class="sr-only">Отметить правильный вариант</span>
                        <svg v-if="editDraft.is_multiple" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 5h16v16H4z" /><path v-if="choice.is_correct" d="m8 13 3 3 5-7" /></svg>
                        <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8" /><circle v-if="choice.is_correct" cx="12" cy="12" r="3" fill="currentColor" stroke="none" /></svg>
                      </button>
                      <input v-model="choice.text" :maxlength="CHOICE_LIMIT" type="text" class="min-w-0 flex-1 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-400">
                      <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-rose-500/10 text-rose-200 transition hover:bg-rose-500/20 hover:text-white" @click="removeChoice(editDraft, choiceIndex)">
                        <span class="sr-only">Удалить вариант</span>
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
                      </button>
                    </div>
                    <button type="button" class="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-300 transition hover:border-slate-500 hover:text-white" @click="addChoice(editDraft)">Добавить вариант</button>
                  </div>
                </div>

                <textarea v-model="editDraft.explanation" data-autogrow rows="2" :maxlength="EXPLANATION_LIMIT" class="mt-4 max-h-56 min-h-[72px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-indigo-400" placeholder="Объяснение" @input="autoGrowTextarea"></textarea>
                <div v-if="editErrors.length" class="mt-3 rounded-2xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-xs text-amber-100">{{ editErrors[0] }}</div>
              </template>

              <template v-else>
                <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-bold text-slate-300">№ {{ index + 1 }}</span>
                      <span class="rounded-full border px-3 py-1 text-xs font-bold" :class="question.is_multiple ? 'border-violet-400/30 bg-violet-400/10 text-violet-200' : 'border-sky-400/30 bg-sky-400/10 text-sky-200'">{{ questionTypeLabel(question) }}</span>
                      <span class="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200">Правильных: {{ correctChoicesCount(question) }}</span>
                    </div>
                    <h3 class="mt-3 text-base font-black leading-6 text-white">{{ question.text }}</h3>
                    <p v-if="question.explanation" class="mt-2 rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm leading-6 text-slate-400">{{ question.explanation }}</p>
                  </div>

                  <div class="flex shrink-0 flex-wrap gap-2">
                    <button type="button" class="group relative grid h-10 w-10 place-items-center rounded-xl border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-slate-500 hover:text-white" @click="copyQuestionToDraft(question)">
                      <span class="sr-only">Дублировать</span>
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 8h10v12H8z" /><path d="M6 16H4V4h12v2" /></svg>
                      <span class="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Дублировать</span>
                    </button>
                    <button type="button" class="group relative grid h-10 w-10 place-items-center rounded-xl border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-slate-500 hover:text-white" @click="startEdit(question)">
                      <span class="sr-only">Редактировать</span>
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                      <span class="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Редактировать</span>
                    </button>
                    <button type="button" class="group relative grid h-10 w-10 place-items-center rounded-xl bg-rose-500/10 text-rose-200 transition hover:bg-rose-500/20 hover:text-white" @click="requestDeleteQuestion(question)">
                      <span class="sr-only">Удалить</span>
                      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v5M14 11v5" /></svg>
                      <span class="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Удалить</span>
                    </button>
                  </div>
                </div>

                <div class="mt-4 grid gap-2 md:grid-cols-2">
                  <div v-for="(choice, choiceIndex) in question.choices" :key="choice.id || choiceIndex" class="rounded-2xl border px-3 py-2 text-sm" :class="choice.is_correct ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-100' : 'border-slate-800 bg-slate-900/70 text-slate-400'">
                    <div class="flex items-start gap-2">
                      <span class="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border text-[10px]" :class="choice.is_correct ? 'border-emerald-400/50 text-emerald-100' : 'border-slate-700 text-slate-500'">{{ choiceIndex + 1 }}</span>
                      <span class="min-w-0 break-words">{{ choice.text }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </article>
          </div>
        </section>
      </div>
    </div>

    <div v-if="confirmDialog.open" class="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm" @mousedown.self="closeConfirmDialog">
      <section class="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div class="flex items-start gap-4">
          <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-rose-400/30 bg-rose-400/10 text-rose-200">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>
          </div>
          <div>
            <h3 class="text-xl font-black text-white">{{ confirmDialog.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-400">{{ confirmDialog.message }}</p>
          </div>
        </div>
        <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button" class="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-60" :disabled="confirmDialog.pending" @click="closeConfirmDialog">
            Отмена
          </button>
          <button type="button" class="rounded-xl bg-rose-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-rose-500 disabled:opacity-60" :disabled="confirmDialog.pending || isDeleting" @click="submitConfirmDialog">
            {{ confirmDialog.pending ? 'Удаление...' : confirmDialog.confirmText }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>
