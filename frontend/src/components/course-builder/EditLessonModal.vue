<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  lesson: { type: Object, default: null },
  attachments: { type: Array, default: () => [] },
  questions: { type: Array, default: () => [] },
  videoStatus: { type: Object, default: null },
})

const emit = defineEmits([
  'close',
  'save',
  'open-quiz-config',
  'regenerate-final-exam',
  'upload-attachment',
  'delete-attachment',
  'create-question',
  'update-question',
  'delete-question',
  'upload-video',
])

const TITLE_LIMIT = 120
const CONTENT_LIMIT = 12000
const QUESTION_LIMIT = 1000
const CHOICE_LIMIT = 500
const EXPLANATION_LIMIT = 2000
const URL_LIMIT = 500
const MAX_ATTACHMENT_SIZE_MB = 50
const MAX_VIDEO_SIZE_MB = 1024

const form = reactive({
  title: '',
  content: '',
  video_url: '',
  is_published: true,
})

const newQuestion = reactive({
  text: '',
  is_multiple: false,
  explanation: '',
  choices: [
    { text: '', is_correct: false },
    { text: '', is_correct: false },
  ],
})

const attachmentFile = ref(null)
const videoSource = ref('file')
const formError = ref('')
const contentTextarea = ref(null)

const confirmDialog = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  action: null,
})

const lessonTypeMeta = {
  video: { label: 'Видео', short: 'VI', tone: 'border-sky-500/40 bg-sky-500/10 text-sky-200' },
  text: { label: 'Текст', short: 'TX', tone: 'border-slate-500/40 bg-slate-500/10 text-slate-200' },
  quiz: { label: 'Тест', short: 'QZ', tone: 'border-violet-500/40 bg-violet-500/10 text-violet-200' },
  final_exam: { label: 'Финальный экзамен', short: 'EX', tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' },
}

const statusLabels = {
  pending: 'Ожидает обработки',
  processing: 'Обрабатывается',
  ready: 'Готово',
  failed: 'Ошибка обработки',
  missing: 'Не загружено',
  inconsistent: 'Неконсистентное состояние',
}

const lessonMeta = computed(() => lessonTypeMeta[props.lesson?.type] || lessonTypeMeta.text)
const lessonTypeLabel = computed(() => lessonMeta.value.label)
const videoStatusLabel = computed(() => statusLabels[props.videoStatus?.status] || props.videoStatus?.status || 'Не загружено')
const isQuizType = computed(() => props.lesson?.type === 'quiz' || props.lesson?.type === 'final_exam')
const isVideoType = computed(() => props.lesson?.type === 'video')
const isTextType = computed(() => props.lesson?.type === 'text')
const isFinalExamType = computed(() => props.lesson?.type === 'final_exam')
const contentLength = computed(() => form.content.length)

const formatFileSize = (size = 0) => {
  if (size >= 1024 * 1024) {
    return `${(size / 1024 / 1024).toFixed(1)} МБ`
  }
  return `${Math.max(1, Math.round(size / 1024))} КБ`
}

const autoGrowElement = (element) => {
  if (!element) {
    return
  }
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 320)}px`
}

const autoGrowTextarea = (event) => {
  autoGrowElement(event.target)
}

watch(
  () => [props.open, props.lesson],
  () => {
    if (!props.open || !props.lesson) {
      return
    }
    form.title = props.lesson.title || ''
    form.content = props.lesson.content || ''
    form.video_url = props.lesson.video_url || ''
    form.is_published = Boolean(props.lesson.is_published)
    videoSource.value = form.video_url ? 'youtube' : 'file'
    formError.value = ''
    nextTick(() => autoGrowElement(contentTextarea.value))
  },
  { immediate: true, deep: true }
)

watch(
  () => form.content,
  () => nextTick(() => autoGrowElement(contentTextarea.value))
)

const saveLesson = () => {
  const title = form.title.trim()
  let content = form.content.trim()
  const videoUrl = form.video_url.trim()

  formError.value = ''

  if (!title) {
    formError.value = 'Укажите название урока.'
    return
  }

  if (title.length > TITLE_LIMIT) {
    formError.value = `Название урока не должно превышать ${TITLE_LIMIT} символов.`
    return
  }

  // ✅ ФИКС ДЛЯ ТЕСТОВ И ЭКЗАМЕНОВ
  if (props.lesson?.type === 'quiz' || props.lesson?.type === 'final_exam') {
    if (!content || content === '') {
      content = ' '
    }
  }

  if (content.length > CONTENT_LIMIT) {
    formError.value = `Содержание урока не должно превышать ${CONTENT_LIMIT} символов.`
    return
  }

  emit('save', {
    title,
    content,
    video_url: isVideoType.value && videoSource.value === 'youtube' ? videoUrl : '',
    is_published: form.is_published,
  })
}


const addChoice = () => {
  if (newQuestion.choices.length >= 8) {
    formError.value = 'Для одного вопроса допускается до 8 вариантов ответа.'
    return
  }
  newQuestion.choices.push({ text: '', is_correct: false })
}

const removeChoice = (index) => {
  if (newQuestion.choices.length <= 2) {
    formError.value = 'Оставьте минимум два варианта ответа.'
    return
  }
  newQuestion.choices.splice(index, 1)
}

const submitNewQuestion = () => {
  const text = newQuestion.text.trim()
  const explanation = newQuestion.explanation.trim()
  const choices = newQuestion.choices
    .map((item) => ({ text: item.text.trim(), is_correct: item.is_correct }))
    .filter((item) => item.text)

  formError.value = ''

  if (!text) {
    formError.value = 'Введите текст вопроса.'
    return
  }

  if (text.length > QUESTION_LIMIT) {
    formError.value = `Вопрос не должен превышать ${QUESTION_LIMIT} символов.`
    return
  }

  if (explanation.length > EXPLANATION_LIMIT) {
    formError.value = `Объяснение не должно превышать ${EXPLANATION_LIMIT} символов.`
    return
  }

  if (choices.length < 2) {
    formError.value = 'Добавьте минимум два варианта ответа.'
    return
  }

  if (!choices.some((item) => item.is_correct)) {
    formError.value = 'Отметьте хотя бы один правильный ответ.'
    return
  }

  emit('create-question', {
    text,
    is_multiple: newQuestion.is_multiple,
    explanation,
    choices,
  })

  newQuestion.text = ''
  newQuestion.is_multiple = false
  newQuestion.explanation = ''
  newQuestion.choices = [
    { text: '', is_correct: false },
    { text: '', is_correct: false },
  ]
}

const chooseAttachment = (event) => {
  attachmentFile.value = event.target.files?.[0] || null
  formError.value = ''

  if (!attachmentFile.value) {
    return
  }

  if (attachmentFile.value.size > MAX_ATTACHMENT_SIZE_MB * 1024 * 1024) {
    formError.value = `Размер материала не должен превышать ${MAX_ATTACHMENT_SIZE_MB} МБ.`
    event.target.value = ''
    return
  }

  emit('upload-attachment', attachmentFile.value)
  event.target.value = ''
}

const chooseVideoFile = (event) => {
  const file = event.target.files?.[0] || null
  formError.value = ''

  if (!file) {
    return
  }

  if (!file.type.startsWith('video/')) {
    formError.value = 'Выберите видеофайл.'
    event.target.value = ''
    return
  }

  if (file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024) {
    formError.value = `Размер видео не должен превышать ${MAX_VIDEO_SIZE_MB} МБ.`
    event.target.value = ''
    return
  }

  emit('upload-video', file)
  event.target.value = ''
}

const openConfirmDialog = ({ title, message, confirmText, action }) => {
  confirmDialog.title = title
  confirmDialog.message = message
  confirmDialog.confirmText = confirmText || 'Удалить'
  confirmDialog.action = action
  confirmDialog.open = true
}

const closeConfirmDialog = () => {
  confirmDialog.open = false
  confirmDialog.action = null
}

const submitConfirmDialog = () => {
  if (confirmDialog.action) {
    confirmDialog.action()
  }
  closeConfirmDialog()
}

const requestDeleteAttachment = (file) => {
  openConfirmDialog({
    title: 'Удалить материал?',
    message: `Файл «${file.original_name}» будет удалён из материалов урока.`,
    confirmText: 'Удалить файл',
    action: () => emit('delete-attachment', file),
  })
}

const requestDeleteQuestion = (question) => {
  openConfirmDialog({
    title: 'Удалить вопрос?',
    message: 'Вопрос и связанные варианты ответа будут удалены из теста.',
    confirmText: 'Удалить вопрос',
    action: () => emit('delete-question', question),
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4">
    <div
      class="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950/50">
      <div
        class="sticky top-0 z-10 flex flex-col gap-3 rounded-t-3xl border-b border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:flex-row sm:items-start sm:justify-between sm:px-6 sm:py-5">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-3">
            <span
              class="inline-flex h-9 w-9 items-center justify-center rounded-xl border text-[10px] font-black tracking-wide"
              :class="lessonMeta.tone">
              {{ lessonMeta.short }}
            </span>
            <div class="min-w-0">
              <h3 class="truncate text-xl font-black text-white sm:text-2xl">Редактор урока</h3>
              <p class="text-sm text-slate-400">Тип урока: {{ lessonTypeLabel }}</p>
            </div>
          </div>
        </div>
        <button type="button"
          class="w-full rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-700 sm:w-auto"
          @click="emit('close')">
          Закрыть
        </button>
      </div>

      <div class="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6">
        <div v-if="formError"
          class="rounded-2xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {{ formError }}
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="md:col-span-2">
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="block text-sm font-semibold text-slate-300">Название урока</label>
              <span class="text-xs text-slate-500">{{ form.title.length }}/{{ TITLE_LIMIT }}</span>
            </div>
            <input v-model.trim="form.title" type="text" :maxlength="TITLE_LIMIT"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-400">
          </div>

          <label
            class="inline-flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-300 md:col-span-2">
            <input v-model="form.is_published" type="checkbox" class="h-4 w-4 accent-indigo-500">
            Опубликован
          </label>

          <div v-if="isVideoType" class="md:col-span-2">
            <div class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
              <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
                <div>
                  <h4 class="text-sm font-bold text-white">Источник видео</h4>
                  <p class="mt-1 text-xs text-slate-400">HLS-файл используется как основной вариант, YouTube — как
                    резервный источник.</p>
                </div>
                <div class="grid grid-cols-2 rounded-xl border border-slate-700 bg-slate-900 p-1">
                  <button type="button" class="rounded-lg px-3 py-2 text-xs font-bold transition"
                    :class="videoSource === 'file' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
                    @click="videoSource = 'file'">
                    HLS-файл
                  </button>
                  <button type="button" class="rounded-lg px-3 py-2 text-xs font-bold transition"
                    :class="videoSource === 'youtube' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
                    @click="videoSource = 'youtube'">
                    YouTube
                  </button>
                </div>
              </div>

              <div v-if="videoSource === 'youtube'" class="mt-4">
                <div class="mb-2 flex items-center justify-between gap-3">
                  <label class="block text-sm font-semibold text-slate-300">Ссылка на YouTube</label>
                  <span class="text-xs text-slate-500">{{ form.video_url.length }}/{{ URL_LIMIT }}</span>
                </div>
                <input v-model.trim="form.video_url" type="url" :maxlength="URL_LIMIT"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
                  placeholder="https://www.youtube.com/watch?v=...">
              </div>

              <div v-else class="mt-4 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-4">
                <label
                  class="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 sm:w-auto">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                    aria-hidden="true">
                    <path d="M12 16V4M7 9l5-5 5 5" />
                    <path d="M20 16v4H4v-4" />
                  </svg>
                  Выбрать видеофайл
                  <input type="file" accept="video/*" class="hidden" @change="chooseVideoFile">
                </label>
                <p class="mt-3 text-xs text-slate-400">После загрузки видео будет обработано в HLS.</p>
                <div class="mt-3 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300">
                  Статус: <span class="font-semibold text-slate-100">{{ videoStatusLabel }}</span>
                </div>
                <p v-if="videoStatus?.error_message"
                  class="mt-2 rounded-xl border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">
                  {{ videoStatus.error_message }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="isVideoType || isTextType" class="md:col-span-2">
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="block text-sm font-semibold text-slate-300">Содержание урока</label>
              <span class="text-xs" :class="contentLength > CONTENT_LIMIT ? 'text-rose-300' : 'text-slate-500'">
                {{ contentLength }}/{{ CONTENT_LIMIT }}
              </span>
            </div>
            <textarea ref="contentTextarea" v-model="form.content" rows="3" :maxlength="CONTENT_LIMIT"
              class="max-h-80 min-h-[96px] w-full resize-none overflow-y-auto rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-indigo-400"
              placeholder="Конспект, инструкции, ссылки или описание практической части..."
              @input="autoGrowTextarea"></textarea>
          </div>
        </div>

        <section class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 class="text-lg font-bold text-white">Материалы к уроку</h4>
              <p class="text-xs text-slate-400">PDF, презентации, архивы и дополнительные файлы.</p>
            </div>
            <label
              class="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-indigo-500 sm:w-auto">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                aria-hidden="true">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Добавить файл
              <input type="file" class="hidden" @change="chooseAttachment">
            </label>
          </div>

          <ul v-if="attachments.length" class="mt-4 space-y-2">
            <li v-for="file in attachments" :key="file.id"
              class="flex items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-900/70 px-3 py-2 text-sm text-slate-200">
              <span class="min-w-0 truncate">{{ file.original_name }} <span class="text-slate-500">({{
                formatFileSize(file.size || 0) }})</span></span>
              <button type="button"
                class="group relative grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-rose-500/15 text-rose-200 transition hover:bg-rose-500/25 hover:text-white"
                @click="requestDeleteAttachment(file)">
                <span class="sr-only">Удалить файл</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18" />
                  <path d="M8 6V4h8v2" />
                  <path d="M19 6l-1 14H6L5 6" />
                  <path d="M10 11v5M14 11v5" />
                </svg>
                <span
                  class="pointer-events-none absolute bottom-full right-0 z-20 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Удалить</span>
              </button>
            </li>
          </ul>
          <p v-else
            class="mt-4 rounded-xl border border-dashed border-slate-700 px-4 py-5 text-center text-sm text-slate-500">
            Материалы пока не добавлены.
          </p>
        </section>

        <section v-if="isQuizType" class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 class="text-lg font-bold text-white">Вопросы теста</h4>
              <p class="text-xs text-slate-400">Настройте вопросы, варианты ответа и правила прохождения.</p>
            </div>
            <div class="grid gap-2 sm:flex sm:flex-wrap">
              <button type="button"
                class="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-indigo-500"
                @click="emit('open-quiz-config')">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                  aria-hidden="true">
                  <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
                  <path
                    d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6 1.8 1.8 0 0 0-.5 1.3V21a2 2 0 0 1-4 0v-.09a1.8 1.8 0 0 0-.5-1.3 1.8 1.8 0 0 0-1-.6 1.8 1.8 0 0 0-1.98.36l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1 1.8 1.8 0 0 0-1.3-.5H2.5a2 2 0 0 1 0-4h.09a1.8 1.8 0 0 0 1.3-.5 1.8 1.8 0 0 0 .6-1 1.8 1.8 0 0 0-.36-1.98l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6 1.8 1.8 0 0 0 .5-1.3V2.5a2 2 0 0 1 4 0v.09a1.8 1.8 0 0 0 .5 1.3 1.8 1.8 0 0 0 1 .6 1.8 1.8 0 0 0 1.98-.36l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.8 1.8 0 0 0 19.4 9c.3.3.6.6 1 .6h.1a2 2 0 0 1 0 4h-.1a1.8 1.8 0 0 0-1 .6Z" />
                </svg>
                Настройки теста
              </button>
              <button v-if="isFinalExamType" type="button"
                class="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-emerald-500"
                @click="emit('regenerate-final-exam')">
                Обновить экзамен
              </button>
            </div>
          </div>

          <div v-if="questions.length" class="mt-4 space-y-3">
            <article v-for="question in questions" :key="question.id"
              class="rounded-2xl border border-slate-700 bg-slate-900 p-3">
              <textarea :value="question.text" rows="2" :maxlength="QUESTION_LIMIT" data-autogrow
                class="max-h-56 min-h-[72px] w-full resize-none overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-indigo-400"
                @input="autoGrowTextarea"
                @change="emit('update-question', question, { ...question, text: $event.target.value.slice(0, QUESTION_LIMIT) })"></textarea>
              <div class="mt-2 flex justify-end">
                <button type="button"
                  class="inline-flex items-center gap-2 rounded-lg bg-rose-500/15 px-3 py-2 text-xs font-bold text-rose-200 transition hover:bg-rose-500/25 hover:text-white"
                  @click="requestDeleteQuestion(question)">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18" />
                    <path d="M8 6V4h8v2" />
                    <path d="M19 6l-1 14H6L5 6" />
                    <path d="M10 11v5M14 11v5" />
                  </svg>
                  Удалить вопрос
                </button>
              </div>
            </article>
          </div>

          <div class="mt-4 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-4">
            <h5 class="text-sm font-bold text-slate-100">Добавить вопрос</h5>
            <textarea v-model="newQuestion.text" rows="2" :maxlength="QUESTION_LIMIT"
              class="mt-3 max-h-56 min-h-[72px] w-full resize-none overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
              placeholder="Текст вопроса" @input="autoGrowTextarea"></textarea>
            <label class="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-slate-300">
              <input v-model="newQuestion.is_multiple" type="checkbox" class="h-4 w-4 accent-indigo-500">
              Несколько правильных ответов
            </label>

            <div class="mt-3 space-y-2">
              <div v-for="(choice, index) in newQuestion.choices" :key="index" class="flex items-center gap-2">
                <input v-model="choice.is_correct" type="checkbox" class="h-4 w-4 accent-emerald-500">
                <input v-model="choice.text" type="text" :maxlength="CHOICE_LIMIT"
                  class="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
                  placeholder="Вариант ответа">
                <button type="button"
                  class="grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white"
                  @click="removeChoice(index)">
                  <span class="sr-only">Удалить вариант</span>
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M5 12h14" />
                  </svg>
                </button>
              </div>
            </div>

            <textarea v-model="newQuestion.explanation" rows="2" :maxlength="EXPLANATION_LIMIT"
              class="mt-3 max-h-56 min-h-[72px] w-full resize-none overflow-y-auto rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
              placeholder="Объяснение ответа, если нужно" @input="autoGrowTextarea"></textarea>

            <div class="mt-3 flex flex-wrap gap-2">
              <button type="button"
                class="rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-slate-200 transition hover:bg-slate-700"
                @click="addChoice">
                Добавить вариант
              </button>
              <button type="button"
                class="rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-indigo-500"
                @click="submitNewQuestion">
                Добавить вопрос
              </button>
            </div>
          </div>
        </section>
      </div>

      <div
        class="sticky bottom-0 flex flex-col gap-3 rounded-b-3xl border-t border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:px-6 sm:py-5">
        <p class="text-xs text-slate-500">Ограничения формы защищают интерфейс от слишком длинных данных; финальную
          проверку лучше держать и на backend.</p>
        <div class="flex flex-col-reverse gap-3 sm:flex-row">
          <button type="button"
            class="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-slate-700"
            @click="emit('close')">
            Отмена
          </button>
          <button type="button"
            class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-500"
            @click="saveLesson">
            Сохранить изменения
          </button>
        </div>
      </div>
    </div>

    <div v-if="confirmDialog.open"
      class="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4">
      <div class="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-5 shadow-2xl shadow-slate-950/50 sm:p-6">
        <div class="flex items-start gap-4">
          <div class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-rose-500/15 text-rose-200">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              aria-hidden="true">
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
              <path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z" />
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-black text-white">{{ confirmDialog.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-400">{{ confirmDialog.message }}</p>
          </div>
        </div>
        <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button"
            class="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-slate-700"
            @click="closeConfirmDialog">
            Отмена
          </button>
          <button type="button"
            class="rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-rose-500"
            @click="submitConfirmDialog">
            {{ confirmDialog.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
