<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AddModuleModal from '../components/course-builder/AddModuleModal.vue'
import EditLessonModal from '../components/course-builder/EditLessonModal.vue'
import QuizConfigModal from '../components/course-builder/QuizConfigModal.vue'
import { useCourseBuilderStore } from '../stores/courseBuilderStore'
import { showError, showSuccess } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const store = useCourseBuilderStore()

const courseId = computed(() => Number(route.params.id))

const TITLE_LIMIT = 120
const CONTENT_LIMIT = 12000
const MAX_VIDEO_SIZE_MB = 1024

const collapsedModules = ref({})
const moduleModalOpen = ref(false)
const moduleModalMode = ref('create')
const moduleEditTarget = ref(null)

const lessonCreateOpen = ref(false)
const lessonVideoSource = ref('file')
const lessonVideoFile = ref(null)
const lessonContentTextarea = ref(null)
const isCreatingLesson = ref(false)
const activeLessonId = ref(null)
const lessonDraft = reactive({
  title: '',
  type: 'video',
  content: '',
  video_url: '',
  is_published: true,
})

const lessonTypeMeta = {
  video: {
    label: 'Видео',
    short: 'VI',
    hint: 'Видеоурок с HLS или YouTube',
    tone: 'border-sky-500/40 bg-sky-500/10 text-sky-200',
    activeTone: 'border-sky-400/70 bg-sky-500/15 text-sky-100',
  },
  text: {
    label: 'Текст',
    short: 'TX',
    hint: 'Текстовый урок и материалы',
    tone: 'border-slate-500/40 bg-slate-500/10 text-slate-200',
    activeTone: 'border-slate-300/60 bg-slate-500/15 text-white',
  },
  quiz: {
    label: 'Тест',
    short: 'QZ',
    hint: 'Вопросы и настройки прохождения',
    tone: 'border-violet-500/40 bg-violet-500/10 text-violet-200',
    activeTone: 'border-violet-400/70 bg-violet-500/15 text-violet-100',
  },
  final_exam: {
    label: 'Экзамен',
    short: 'EX',
    hint: 'Итоговая проверка курса',
    tone: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
    activeTone: 'border-emerald-400/70 bg-emerald-500/15 text-emerald-100',
  },
}

const getLessonTypeMeta = (type) => lessonTypeMeta[type] || lessonTypeMeta.text

const editingLesson = ref(null)
const editLessonOpen = ref(false)
const editingAttachments = ref([])
const editingQuestions = ref([])
const editingVideoStatus = ref(null)

const quizConfigOpen = ref(false)
const quizConfig = ref(null)

const dirtyLessons = ref(new Map())
let autosaveTimer = null

const confirmDialog = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  pending: false,
  action: null,
})

const selectedModuleId = computed(() => store.selectedModuleId)
const modules = computed(() => store.modules)
const selectedModule = computed(() => store.selectedModule)
const selectedLessons = computed(() => store.selectedLessons)
const lessonVideoFileName = computed(() => lessonVideoFile.value?.name || '')
const lessonDraftContentLength = computed(() => lessonDraft.content.length)

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

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/teacher')
}

const lessonCountForModule = (moduleId) => (store.lessonsByModule[moduleId] || []).length

const loadLessonsForModule = async (moduleId) => {
  if (!moduleId) {
    return
  }
  try {
    await store.fetchLessons(courseId.value, moduleId)
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить уроки модуля.')
  }
}

const init = async () => {
  try {
    await store.fetchModules(courseId.value)
    if (store.selectedModuleId) {
      await loadLessonsForModule(store.selectedModuleId)
    }
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить конструктор курса.')
  }
}

const selectModule = async (moduleId) => {
  activeLessonId.value = null
  store.setSelectedModule(moduleId)
  await loadLessonsForModule(moduleId)
}

const toggleModule = (moduleId) => {
  collapsedModules.value = {
    ...collapsedModules.value,
    [moduleId]: !collapsedModules.value[moduleId],
  }
}

const openCreateModule = () => {
  moduleModalMode.value = 'create'
  moduleEditTarget.value = null
  moduleModalOpen.value = true
}

const openEditModule = (module) => {
  moduleModalMode.value = 'edit'
  moduleEditTarget.value = module
  moduleModalOpen.value = true
}

const submitModuleModal = async ({ title }) => {
  try {
    if (moduleModalMode.value === 'edit' && moduleEditTarget.value) {
      await store.updateModule(moduleEditTarget.value.id, { title })
      showSuccess('Модуль обновлён.')
    } else {
      const created = await store.createModule(courseId.value, { title, order: modules.value.length })
      showSuccess('Модуль создан.')
      await selectModule(created.id)
    }
    moduleModalOpen.value = false
  } catch (error) {
    console.error(error)
    showError('Не удалось сохранить модуль.')
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
  if (confirmDialog.pending) {
    return
  }
  confirmDialog.open = false
  confirmDialog.action = null
}

const submitConfirmDialog = async () => {
  if (!confirmDialog.action) {
    return
  }

  confirmDialog.pending = true
  try {
    await confirmDialog.action()
    confirmDialog.open = false
    confirmDialog.action = null
  } finally {
    confirmDialog.pending = false
  }
}

const requestDeleteModule = (module) => {
  openConfirmDialog({
    title: 'Удалить модуль?',
    message: `Модуль «${module.title}» будет удалён вместе с уроками внутри него. Это действие нельзя отменить.`,
    confirmText: 'Удалить модуль',
    action: async () => {
      try {
        await store.deleteModule(module.id)
        showSuccess('Модуль удалён.')
        if (store.selectedModuleId) {
          await loadLessonsForModule(store.selectedModuleId)
        }
      } catch (error) {
        console.error(error)
        showError('Не удалось удалить модуль.')
      }
    },
  })
}

const moveModule = async (moduleId, direction) => {
  const list = [...modules.value]
  const index = list.findIndex((item) => item.id === moduleId)
  const targetIndex = index + direction
  if (index < 0 || targetIndex < 0 || targetIndex >= list.length) {
    return
  }

  ;[list[index], list[targetIndex]] = [list[targetIndex], list[index]]

  try {
    await store.reorderModules(courseId.value, list.map((item) => item.id))
  } catch (error) {
    console.error(error)
    showError('Не удалось изменить порядок модулей.')
  }
}

const resetLessonDraft = () => {
  lessonDraft.title = ''
  lessonDraft.type = 'video'
  lessonDraft.content = ''
  lessonDraft.video_url = ''
  lessonDraft.is_published = true
  lessonVideoSource.value = 'file'
  lessonVideoFile.value = null
  nextTick(() => autoGrowElement(lessonContentTextarea.value))
}

const openCreateLesson = () => {
  if (!selectedModule.value) {
    showError('Сначала выберите модуль.')
    return
  }

  resetLessonDraft()
  lessonCreateOpen.value = true
}

const closeCreateLesson = () => {
  if (isCreatingLesson.value) {
    return
  }
  lessonCreateOpen.value = false
}

const handleCreateVideoFile = (event) => {
  const file = event.target.files?.[0] || null
  if (!file) {
    lessonVideoFile.value = null
    return
  }

  if (!file.type.startsWith('video/')) {
    showError('Выберите видеофайл.')
    event.target.value = ''
    return
  }

  if (file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024) {
    showError(`Размер видео не должен превышать ${MAX_VIDEO_SIZE_MB} МБ.`)
    event.target.value = ''
    return
  }

  lessonVideoFile.value = file
}

const submitCreateLesson = async () => {
  if (!selectedModule.value) {
    showError('Сначала выберите модуль.')
    return
  }

  const title = lessonDraft.title.trim()
  const content = lessonDraft.content.trim()
  const youtubeUrl = lessonDraft.video_url.trim()

  if (!title) {
    showError('Укажите название урока.')
    return
  }

  if (title.length > TITLE_LIMIT) {
    showError(`Название урока не должно превышать ${TITLE_LIMIT} символов.`)
    return
  }

  if (content.length > CONTENT_LIMIT) {
    showError(`Содержание урока не должно превышать ${CONTENT_LIMIT} символов.`)
    return
  }

  if (lessonDraft.type === 'video') {
    const hasYoutubeUrl = lessonVideoSource.value === 'youtube' && youtubeUrl
    const hasVideoFile = lessonVideoSource.value === 'file' && lessonVideoFile.value

    if (!hasYoutubeUrl && !hasVideoFile) {
      showError('Для видеоурока выберите HLS-файл или укажите ссылку YouTube.')
      return
    }
  }

  isCreatingLesson.value = true

  try {
    const createdLesson = await store.createLesson({
      module: selectedModule.value.id,
      title,
      type: lessonDraft.type,
      content,
      video_url: lessonDraft.type === 'video' && lessonVideoSource.value === 'youtube' ? youtubeUrl : '',
      is_published: lessonDraft.is_published,
      order: selectedLessons.value.length,
    })

    activeLessonId.value = createdLesson.id

    if (lessonDraft.type === 'video' && lessonVideoSource.value === 'file' && lessonVideoFile.value) {
      try {
        await store.uploadLessonVideo(createdLesson.id, lessonVideoFile.value)
        showSuccess('Урок создан. Видео отправлено на HLS-обработку.')
      } catch (uploadError) {
        console.error(uploadError)
        showError('Урок создан, но видео не загрузилось. Откройте редактор и повторите загрузку.')
      }
    } else {
      showSuccess('Урок создан.')
    }

    lessonCreateOpen.value = false
    resetLessonDraft()
    await loadLessonsForModule(selectedModule.value.id)
  } catch (error) {
    console.error(error)
    showError(error.response?.data?.error || error.response?.data?.detail || 'Не удалось создать урок.')
  } finally {
    isCreatingLesson.value = false
  }
}

const moveLesson = async (lessonId, direction) => {
  if (!selectedModule.value) {
    return
  }

  const list = [...selectedLessons.value]
  const index = list.findIndex((item) => item.id === lessonId)
  const targetIndex = index + direction
  if (index < 0 || targetIndex < 0 || targetIndex >= list.length) {
    return
  }

  ;[list[index], list[targetIndex]] = [list[targetIndex], list[index]]

  try {
    await store.reorderLessons(selectedModule.value.id, list.map((item) => item.id))
  } catch (error) {
    console.error(error)
    showError('Не удалось изменить порядок уроков.')
  }
}

const requestDeleteLesson = (lesson) => {
  if (!selectedModule.value) {
    return
  }

  const moduleId = selectedModule.value.id
  openConfirmDialog({
    title: 'Удалить урок?',
    message: `Урок «${lesson.title}» будет удалён из выбранного модуля. Это действие нельзя отменить.`,
    confirmText: 'Удалить урок',
    action: async () => {
      try {
        await store.deleteLesson(lesson.id, moduleId)
        if (activeLessonId.value === lesson.id) {
          activeLessonId.value = null
        }
        showSuccess('Урок удалён.')
      } catch (error) {
        console.error(error)
        showError('Не удалось удалить урок.')
      }
    },
  })
}

const markLessonDirty = (lesson, patch) => {
  activeLessonId.value = lesson.id
  Object.assign(lesson, patch)
  dirtyLessons.value.set(lesson.id, {
    ...(dirtyLessons.value.get(lesson.id) || {}),
    ...patch,
  })
}

const flushAutosave = async () => {
  if (!selectedModule.value || !dirtyLessons.value.size) {
    return
  }

  const currentDirty = new Map(dirtyLessons.value)
  dirtyLessons.value.clear()

  for (const [lessonId, patch] of currentDirty.entries()) {
    try {
      await store.updateLesson(lessonId, patch, selectedModule.value.id)
    } catch (error) {
      console.error(error)
      dirtyLessons.value.set(lessonId, patch)
    }
  }

  if (!dirtyLessons.value.size) {
    showSuccess('Сохранено')
  }
}

const openEditLesson = async (lesson) => {
  activeLessonId.value = lesson.id
  editingLesson.value = lesson
  editLessonOpen.value = true

  try {
    editingAttachments.value = await store.fetchAttachments(lesson.id)
    if (lesson.type === 'quiz' || lesson.type === 'final_exam') {
      editingQuestions.value = await store.fetchQuestions(lesson.id)
      quizConfig.value = await store.getQuizConfig(lesson.id)
    } else {
      editingQuestions.value = []
      quizConfig.value = null
    }

    if (lesson.type === 'video') {
      editingVideoStatus.value = await store.getLessonVideoManifest(lesson.id)
    } else {
      editingVideoStatus.value = null
    }
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить данные урока.')
  }
}

const saveLessonFromModal = async (patch) => {
  if (!editingLesson.value || !selectedModule.value) {
    return
  }

  const title = String(patch.title || '').trim()
  const content = String(patch.content || '').trim()

  if (!title) {
    showError('Укажите название урока.')
    return
  }

  if (title.length > TITLE_LIMIT) {
    showError(`Название урока не должно превышать ${TITLE_LIMIT} символов.`)
    return
  }

  if (content.length > CONTENT_LIMIT) {
    showError(`Содержание урока не должно превышать ${CONTENT_LIMIT} символов.`)
    return
  }

  try {
    const updated = await store.updateLesson(
      editingLesson.value.id,
      {
        ...patch,
        title,
        content,
      },
      selectedModule.value.id
    )
    editingLesson.value = updated
    activeLessonId.value = updated.id
    showSuccess('Урок обновлён.')
  } catch (error) {
    console.error(error)
    showError('Не удалось обновить урок.')
  }
}

const openQuizConfig = () => {
  quizConfigOpen.value = true
}

const saveQuizConfig = async (payload) => {
  if (!editingLesson.value) {
    return
  }

  try {
    quizConfig.value = await store.saveQuizConfig(editingLesson.value.id, payload)
    quizConfigOpen.value = false
    showSuccess('Настройки теста сохранены.')
  } catch (error) {
    console.error(error)
    showError('Не удалось сохранить настройки теста.')
  }
}

const regenerateFinalExam = async () => {
  try {
    await store.generateFinalExam(courseId.value)
    showSuccess('Финальный экзамен сгенерирован.')
    await init()
  } catch (error) {
    console.error(error)
    showError(error.response?.data?.error || 'Не удалось сгенерировать экзамен.')
  }
}

const uploadAttachment = async (file) => {
  if (!editingLesson.value) {
    return
  }

  try {
    const saved = await store.uploadAttachment(editingLesson.value.id, file)
    editingAttachments.value = [saved, ...editingAttachments.value]
    showSuccess('Файл прикреплён.')
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить вложение.')
  }
}

const removeAttachment = async (attachment) => {
  try {
    await store.deleteAttachment(attachment.id)
    editingAttachments.value = editingAttachments.value.filter((item) => item.id !== attachment.id)
    showSuccess('Вложение удалено.')
  } catch (error) {
    console.error(error)
    showError('Не удалось удалить вложение.')
  }
}

const uploadVideo = async (file) => {
  if (!editingLesson.value) {
    return
  }

  if (!file.type.startsWith('video/')) {
    showError('Выберите видеофайл.')
    return
  }

  if (file.size > MAX_VIDEO_SIZE_MB * 1024 * 1024) {
    showError(`Размер видео не должен превышать ${MAX_VIDEO_SIZE_MB} МБ.`)
    return
  }

  try {
    const result = await store.uploadLessonVideo(editingLesson.value.id, file)
    editingVideoStatus.value = {
      status: result.status || 'pending',
      m3u8_url: '',
      error_message: '',
    }
    showSuccess('Видео загружено, началась HLS-обработка.')
  } catch (error) {
    console.error(error)
    showError('Не удалось загрузить видео.')
  }
}

const createQuestion = async (payload) => {
  if (!editingLesson.value) {
    return
  }

  try {
    const created = await store.createQuestion(editingLesson.value.id, payload)
    editingQuestions.value = [...editingQuestions.value, created]
    showSuccess('Вопрос добавлен.')
  } catch (error) {
    console.error(error)
    showError('Не удалось добавить вопрос.')
  }
}

const updateQuestion = async (question, payload) => {
  try {
    const updated = await store.updateQuestion(question.id, payload)
    editingQuestions.value = editingQuestions.value.map((item) => (item.id === question.id ? updated : item))
  } catch (error) {
    console.error(error)
    showError('Не удалось обновить вопрос.')
  }
}

const deleteQuestion = async (question) => {
  try {
    await store.deleteQuestion(question.id)
    editingQuestions.value = editingQuestions.value.filter((item) => item.id !== question.id)
    showSuccess('Вопрос удалён.')
  } catch (error) {
    console.error(error)
    showError('Не удалось удалить вопрос.')
  }
}

const previewLesson = (lesson) => {
  activeLessonId.value = lesson.id
  window.open(`/course/${courseId.value}/lesson/${lesson.id}?preview=1`, '_blank')
}

watch(
  () => store.selectedModuleId,
  async (moduleId) => {
    if (moduleId) {
      await loadLessonsForModule(moduleId)
    }
  }
)

watch(
  () => lessonDraft.content,
  () => nextTick(() => autoGrowElement(lessonContentTextarea.value))
)

watch(
  () => lessonDraft.type,
  (type) => {
    if (type !== 'video') {
      lessonVideoSource.value = 'file'
      lessonVideoFile.value = null
      lessonDraft.video_url = ''
    }
  }
)

onMounted(async () => {
  await init()
  autosaveTimer = window.setInterval(flushAutosave, 30000)
})

onUnmounted(() => {
  if (autosaveTimer) {
    window.clearInterval(autosaveTimer)
  }
})
</script>

<template>
  <div class="mx-auto mt-4 max-w-7xl px-0 pb-12 sm:mt-8 sm:px-4">
    <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
      <div class="min-w-0">
        <button
          type="button"
          class="btn-secondary mb-4 inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold"
          @click="goBack"
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Назад
        </button>
        <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300/80">Панель преподавателя</p>
        <h1 class="mt-2 break-words text-2xl font-black text-slate-100 md:text-4xl">Конструктор курса</h1>
      </div>
      <button
        type="button"
        class="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-2.5 text-center text-sm font-semibold text-emerald-200 shadow-lg shadow-emerald-950/20 transition hover:border-emerald-300/40 hover:bg-emerald-500/15 sm:w-auto"
        @click="regenerateFinalExam"
      >
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1m0-12.8-2.1 2.1m-8.6 8.6-2.1 2.1" />
        </svg>
        Сгенерировать финальный экзамен
      </button>
    </div>

    <div class="grid gap-6 xl:grid-cols-[360px,minmax(0,1fr)]">
      <aside class="card-glass min-w-0 rounded-3xl p-4">
        <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-lg font-bold text-white">Модули курса</h2>
            <p class="text-xs text-slate-400">Выберите модуль для работы с уроками</p>
          </div>
          <button
            type="button"
            class="btn-primary inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold"
            @click="openCreateModule"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Модуль
          </button>
        </div>

        <div v-if="!modules.length" class="rounded-2xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
          Пока нет модулей. Создайте первый модуль курса.
        </div>

        <div v-else class="max-h-[62vh] space-y-3 overflow-y-auto pr-1 xl:max-h-none xl:overflow-visible">
          <article
            v-for="(module, index) in modules"
            :key="module.id"
            class="rounded-2xl border p-3 transition"
            :class="selectedModuleId === module.id ? 'border-indigo-400/50 bg-indigo-500/10 shadow-lg shadow-indigo-950/20' : 'border-slate-700 bg-slate-950/50 hover:border-slate-600'"
          >
            <div class="flex items-start gap-3">
              <button
                type="button"
                class="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-indigo-400/50 hover:text-white"
                :title="collapsedModules[module.id] ? 'Показать уроки' : 'Скрыть уроки'"
                @click="toggleModule(module.id)"
              >
                <svg v-if="collapsedModules[module.id]" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M9 6l6 6-6 6" />
                </svg>
                <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </button>

              <button type="button" class="min-w-0 flex-1 text-left" @click="selectModule(module.id)">
                <span class="block line-clamp-2 text-sm font-bold" :class="selectedModuleId === module.id ? 'text-indigo-100' : 'text-slate-100'">
                  {{ module.title }}
                </span>
                <span class="mt-1 block text-xs text-slate-400">
                  {{ lessonCountForModule(module.id) }} урок(ов)
                </span>
              </button>

              <span v-if="selectedModuleId === module.id" class="rounded-full border border-indigo-400/40 bg-indigo-400/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-indigo-200">
                Активен
              </span>
            </div>

            <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-800 pt-3">
              <button type="button" class="group relative grid h-8 w-8 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-40" :disabled="index === 0" @click="moveModule(module.id, -1)">
                <span class="sr-only">Поднять модуль</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Вверх</span>
              </button>
              <button type="button" class="group relative grid h-8 w-8 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-40" :disabled="index === modules.length - 1" @click="moveModule(module.id, 1)">
                <span class="sr-only">Опустить модуль</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M19 12l-7 7-7-7" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Вниз</span>
              </button>
              <button type="button" class="group relative grid h-8 w-8 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white" @click="openEditModule(module)">
                <span class="sr-only">Редактировать модуль</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Изменить</span>
              </button>
              <button type="button" class="group relative ml-auto grid h-8 w-8 place-items-center rounded-lg bg-rose-500/15 text-rose-200 transition hover:bg-rose-500/25 hover:text-white" @click="requestDeleteModule(module)">
                <span class="sr-only">Удалить модуль</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v5M14 11v5" /></svg>
                <span class="pointer-events-none absolute bottom-full right-0 z-20 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Удалить</span>
              </button>
            </div>

            <div v-if="!collapsedModules[module.id]" class="mt-3 border-t border-slate-800 pt-3">
              <div v-if="lessonCountForModule(module.id)" class="max-h-48 space-y-1.5 overflow-y-auto pr-1 text-xs text-slate-400">
                <button
                  v-for="lesson in store.lessonsByModule[module.id] || []"
                  :key="lesson.id"
                  type="button"
                  class="flex w-full items-center gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-slate-900/80"
                  :class="activeLessonId === lesson.id ? 'bg-indigo-500/10 text-indigo-100' : ''"
                  @click="selectModule(module.id)"
                >
                  <span class="h-1.5 w-1.5 rounded-full" :class="lesson.is_published ? 'bg-emerald-400' : 'bg-amber-300'"></span>
                  <span class="line-clamp-2">{{ lesson.title }}</span>
                </button>
              </div>
              <p v-else class="text-xs text-slate-500">В модуле пока нет уроков.</p>
            </div>
          </article>
        </div>
      </aside>

      <section class="card-glass min-w-0 rounded-3xl p-4">
        <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Рабочая область</p>
            <h2 class="mt-1 break-words text-xl font-bold text-white">
              {{ selectedModule ? selectedModule.title : 'Модуль не выбран' }}
            </h2>
            <p v-if="selectedModule" class="mt-1 text-sm text-slate-400">
              {{ selectedLessons.length }} урок(ов) в выбранном модуле
            </p>
          </div>
          <button
            type="button"
            class="btn-primary inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold sm:w-auto"
            :disabled="!selectedModule"
            @click="openCreateLesson"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Добавить урок
          </button>
        </div>

        <div v-if="!selectedModule" class="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <p class="text-base font-semibold text-slate-300">Выберите модуль слева</p>
          <p class="mt-2 text-sm text-slate-500">После выбора здесь появится список уроков и быстрые действия.</p>
        </div>

        <div v-else-if="!selectedLessons.length" class="rounded-2xl border border-dashed border-slate-700 p-10 text-center">
          <p class="text-base font-semibold text-slate-300">В этом модуле пока нет уроков</p>
          <p class="mt-2 text-sm text-slate-500">Создайте видео, текстовый урок, тест или финальный экзамен.</p>
        </div>

        <div v-else class="space-y-3">
          <article
            v-for="(lesson, index) in selectedLessons"
            :key="lesson.id"
            class="grid min-w-0 gap-3 rounded-2xl border p-3 transition xl:grid-cols-[56px,minmax(0,1fr),160px,auto] xl:items-center"
            :class="activeLessonId === lesson.id ? 'border-indigo-400/60 bg-indigo-500/10 shadow-lg shadow-indigo-950/20' : 'border-slate-700 bg-slate-950/55 hover:border-slate-600'"
            @click="activeLessonId = lesson.id"
          >
            <div class="flex items-center gap-3 xl:block">
              <span
                class="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border text-[11px] font-black tracking-wide"
                :class="getLessonTypeMeta(lesson.type).tone"
                :title="getLessonTypeMeta(lesson.type).label"
              >
                {{ getLessonTypeMeta(lesson.type).short }}
              </span>
              <div class="min-w-0 xl:hidden">
                <p class="line-clamp-2 text-sm font-bold text-slate-100">{{ lesson.title }}</p>
                <p class="text-xs text-slate-500">{{ getLessonTypeMeta(lesson.type).label }}</p>
              </div>
            </div>

            <div class="min-w-0" @click.stop>
              <label class="sr-only" :for="`lesson-title-${lesson.id}`">Название урока</label>
              <input
                :id="`lesson-title-${lesson.id}`"
                :value="lesson.title"
                :maxlength="TITLE_LIMIT"
                class="input-control w-full min-w-0 rounded-xl bg-slate-900 px-3 py-2.5 font-semibold"
                @focus="activeLessonId = lesson.id"
                @change="markLessonDirty(lesson, { title: $event.target.value.slice(0, TITLE_LIMIT) })"
              >
              <p class="mt-1 text-xs text-slate-500">{{ getLessonTypeMeta(lesson.type).label }}</p>
            </div>

            <div class="flex flex-wrap items-center gap-2" @click.stop>
              <span
                class="inline-flex min-w-[96px] items-center justify-center rounded-full border px-3 py-1.5 text-xs font-semibold"
                :class="lesson.is_published ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200' : 'border-amber-400/30 bg-amber-400/10 text-amber-200'"
              >
                {{ lesson.is_published ? 'Опубликован' : 'Черновик' }}
              </span>
              <button
                type="button"
                class="group relative grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white"
                @click="markLessonDirty(lesson, { is_published: !lesson.is_published })"
              >
                <span class="sr-only">Изменить публикацию</span>
                <svg v-if="lesson.is_published" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-5" /><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 2" /><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">
                  {{ lesson.is_published ? 'Снять с публикации' : 'Опубликовать' }}
                </span>
              </button>
            </div>

            <div class="flex flex-wrap items-center gap-2 xl:justify-end" @click.stop>
              <button type="button" class="group relative grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-40" :disabled="index === 0" @click="moveLesson(lesson.id, -1)">
                <span class="sr-only">Поднять урок</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Вверх</span>
              </button>
              <button type="button" class="group relative grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-40" :disabled="index === selectedLessons.length - 1" @click="moveLesson(lesson.id, 1)">
                <span class="sr-only">Опустить урок</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M19 12l-7 7-7-7" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Вниз</span>
              </button>
              <button type="button" class="group relative grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white" @click="openEditLesson(lesson)">
                <span class="sr-only">Редактировать урок</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Редактировать</span>
              </button>
              <button type="button" class="group relative grid h-9 w-9 place-items-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 hover:text-white" @click="previewLesson(lesson)">
                <span class="sr-only">Предпросмотр урока</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" /></svg>
                <span class="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Предпросмотр</span>
              </button>
              <button type="button" class="group relative grid h-9 w-9 place-items-center rounded-lg bg-rose-500/15 text-rose-200 transition hover:bg-rose-500/25 hover:text-white" @click="requestDeleteLesson(lesson)">
                <span class="sr-only">Удалить урок</span>
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v5M14 11v5" /></svg>
                <span class="pointer-events-none absolute bottom-full right-0 z-20 mb-2 whitespace-nowrap rounded-md bg-slate-950 px-2 py-1 text-[11px] text-slate-200 opacity-0 shadow-lg transition group-hover:opacity-100">Удалить</span>
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <AddModuleModal
      :open="moduleModalOpen"
      :mode="moduleModalMode"
      :initial-title="moduleEditTarget?.title || ''"
      @close="moduleModalOpen = false"
      @submit="submitModuleModal"
    />

    <div v-if="lessonCreateOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4">
      <div class="modal-panel mx-auto my-4 flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl sm:my-8">
        <div class="sticky top-0 z-10 flex flex-col gap-3 rounded-t-3xl border-b border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:flex-row sm:items-start sm:justify-between sm:px-6 sm:py-5">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300/80">{{ selectedModule?.title }}</p>
            <h3 class="mt-1 text-xl font-black text-white sm:text-2xl">Новый урок</h3>
            <p class="mt-1 text-sm text-slate-400">Создайте урок и сразу добавьте основной источник контента.</p>
          </div>
          <button type="button" class="rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-700" @click="closeCreateLesson">
            Закрыть
          </button>
        </div>

        <div class="flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-6">
          <div>
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="block text-sm font-semibold text-slate-300">Название урока</label>
              <span class="text-xs text-slate-500">{{ lessonDraft.title.length }}/{{ TITLE_LIMIT }}</span>
            </div>
            <input
              v-model.trim="lessonDraft.title"
              type="text"
              :maxlength="TITLE_LIMIT"
              class="input-control bg-slate-950 px-4 py-3"
              placeholder="Например: Введение в REST API"
            >
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-300">Тип урока</label>
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <button
                v-for="(meta, type) in lessonTypeMeta"
                :key="type"
                type="button"
                class="rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:border-indigo-400/60"
                :class="lessonDraft.type === type ? meta.activeTone : 'border-slate-700 bg-slate-950 text-slate-300'"
                @click="lessonDraft.type = type"
              >
                <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-current/30 text-[10px] font-black tracking-wide">{{ meta.short }}</span>
                <span class="mt-3 block text-sm font-bold">{{ meta.label }}</span>
                <span class="mt-1 block text-xs text-slate-400">{{ meta.hint }}</span>
              </button>
            </div>
          </div>

          <div v-if="lessonDraft.type === 'video'" class="rounded-2xl border border-slate-700 bg-slate-950/70 p-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
              <div>
                <h4 class="text-sm font-bold text-white">Источник видео</h4>
                <p class="mt-1 text-xs text-slate-400">По умолчанию используется HLS-файл. YouTube оставлен как резервный вариант.</p>
              </div>
              <div class="flex rounded-xl border border-slate-700 bg-slate-900 p-1">
                <button
                  type="button"
                  class="rounded-lg px-3 py-2 text-xs font-bold transition"
                  :class="lessonVideoSource === 'file' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
                  @click="lessonVideoSource = 'file'"
                >
                  HLS-файл
                </button>
                <button
                  type="button"
                  class="rounded-lg px-3 py-2 text-xs font-bold transition"
                  :class="lessonVideoSource === 'youtube' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'"
                  @click="lessonVideoSource = 'youtube'"
                >
                  YouTube
                </button>
              </div>
            </div>

            <div v-if="lessonVideoSource === 'file'" class="mt-4 rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-4">
                <label class="btn-primary inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold sm:w-auto">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M12 16V4M7 9l5-5 5 5" /><path d="M20 16v4H4v-4" />
                </svg>
                Выбрать видеофайл
                <input type="file" accept="video/*" class="hidden" @change="handleCreateVideoFile">
              </label>
              <p class="mt-3 text-xs text-slate-400">
                Файл будет загружен и отправлен на HLS-обработку после создания урока.
              </p>
              <p v-if="lessonVideoFileName" class="mt-2 truncate rounded-lg border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-200">
                Выбран файл: {{ lessonVideoFileName }}
              </p>
            </div>

            <div v-else class="mt-4">
              <label class="mb-2 block text-sm font-semibold text-slate-300">Ссылка на YouTube</label>
              <input
                v-model.trim="lessonDraft.video_url"
                type="url"
                maxlength="500"
                class="input-control bg-slate-950 px-4 py-3"
                placeholder="https://www.youtube.com/watch?v=..."
              >
            </div>
          </div>

          <div v-if="lessonDraft.type === 'video' || lessonDraft.type === 'text'">
            <div class="mb-2 flex items-center justify-between gap-3">
              <label class="block text-sm font-semibold text-slate-300">Содержание урока</label>
              <span class="text-xs" :class="lessonDraftContentLength > CONTENT_LIMIT ? 'text-rose-300' : 'text-slate-500'">
                {{ lessonDraftContentLength }}/{{ CONTENT_LIMIT }}
              </span>
            </div>
            <textarea
              ref="lessonContentTextarea"
              v-model="lessonDraft.content"
              rows="3"
              :maxlength="CONTENT_LIMIT"
              class="input-control max-h-80 min-h-[96px] w-full resize-none overflow-y-auto bg-slate-950 px-4 py-3"
              placeholder="Краткий конспект, инструкции, ссылки или описание практической части..."
              @input="autoGrowTextarea"
            ></textarea>
          </div>

          <label class="inline-flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-300">
            <input v-model="lessonDraft.is_published" type="checkbox" class="h-4 w-4 accent-indigo-500">
            Опубликовать урок сразу
          </label>
        </div>

        <div class="flex flex-col-reverse gap-3 border-t border-slate-800 px-4 py-4 sm:flex-row sm:justify-end sm:px-6 sm:py-5">
          <button type="button" class="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-slate-700" :disabled="isCreatingLesson" @click="closeCreateLesson">
            Отмена
          </button>
          <button type="button" class="btn-primary rounded-xl px-5 py-2.5 text-sm font-bold" :disabled="isCreatingLesson" @click="submitCreateLesson">
            {{ isCreatingLesson ? 'Создание...' : 'Создать урок' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="confirmDialog.open" class="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur-sm sm:p-4">
      <div class="modal-panel w-full max-w-md rounded-3xl p-6">
        <div class="flex items-start gap-4">
          <div class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-rose-500/15 text-rose-200">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z" />
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-black text-white">{{ confirmDialog.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-400">{{ confirmDialog.message }}</p>
          </div>
        </div>
        <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button type="button" class="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-slate-700" :disabled="confirmDialog.pending" @click="closeConfirmDialog">
            Отмена
          </button>
          <button type="button" class="rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-rose-500 disabled:cursor-wait disabled:opacity-70" :disabled="confirmDialog.pending" @click="submitConfirmDialog">
            {{ confirmDialog.pending ? 'Удаление...' : confirmDialog.confirmText }}
          </button>
        </div>
      </div>
    </div>

    <EditLessonModal
      :open="editLessonOpen"
      :lesson="editingLesson"
      :attachments="editingAttachments"
      :questions="editingQuestions"
      :video-status="editingVideoStatus"
      @close="editLessonOpen = false"
      @save="saveLessonFromModal"
      @open-quiz-config="openQuizConfig"
      @regenerate-final-exam="regenerateFinalExam"
      @upload-attachment="uploadAttachment"
      @upload-video="uploadVideo"
      @delete-attachment="removeAttachment"
      @create-question="createQuestion"
      @update-question="updateQuestion"
      @delete-question="deleteQuestion"
    />

    <QuizConfigModal
      :open="quizConfigOpen"
      :value="quizConfig"
      @close="quizConfigOpen = false"
      @save="saveQuizConfig"
    />
  </div>
</template>
