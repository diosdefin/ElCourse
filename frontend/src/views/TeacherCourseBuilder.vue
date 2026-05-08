<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AddModuleModal from '../components/course-builder/AddModuleModal.vue'
import EditLessonModal from '../components/course-builder/EditLessonModal.vue'
import QuizConfigModal from '../components/course-builder/QuizConfigModal.vue'
import { useCourseBuilderStore } from '../stores/courseBuilderStore'
import { showError, showSuccess } from '../utils/toast'

const route = useRoute()
const store = useCourseBuilderStore()

const courseId = computed(() => Number(route.params.id))

const collapsedModules = ref({})
const moduleModalOpen = ref(false)
const moduleModalMode = ref('create')
const moduleEditTarget = ref(null)

const lessonCreateOpen = ref(false)
const lessonDraft = reactive({
  title: '',
  type: 'video',
  content: '',
  video_url: '',
  is_published: true,
})

const editingLesson = ref(null)
const editLessonOpen = ref(false)
const editingAttachments = ref([])
const editingQuestions = ref([])
const editingVideoStatus = ref(null)

const quizConfigOpen = ref(false)
const quizConfig = ref(null)

const dirtyLessons = ref(new Map())
let autosaveTimer = null

const selectedModuleId = computed(() => store.selectedModuleId)
const modules = computed(() => store.modules)
const selectedModule = computed(() => store.selectedModule)
const selectedLessons = computed(() => store.selectedLessons)

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
      showSuccess('Модуль обновлен.')
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

const deleteModule = async (module) => {
  if (!window.confirm(`Удалить модуль "${module.title}"?`)) {
    return
  }

  try {
    await store.deleteModule(module.id)
    showSuccess('Модуль удален.')
    if (store.selectedModuleId) {
      await loadLessonsForModule(store.selectedModuleId)
    }
  } catch (error) {
    console.error(error)
    showError('Не удалось удалить модуль.')
  }
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

const openCreateLesson = () => {
  if (!selectedModule.value) {
    showError('Сначала выберите модуль.')
    return
  }

  lessonDraft.title = ''
  lessonDraft.type = 'video'
  lessonDraft.content = ''
  lessonDraft.video_url = ''
  lessonDraft.is_published = true
  lessonCreateOpen.value = true
}

const submitCreateLesson = async () => {
  if (!selectedModule.value || !lessonDraft.title.trim()) {
    return
  }

  try {
    await store.createLesson({
      module: selectedModule.value.id,
      title: lessonDraft.title.trim(),
      type: lessonDraft.type,
      content: lessonDraft.content,
      video_url: lessonDraft.video_url,
      is_published: lessonDraft.is_published,
      order: selectedLessons.value.length,
    })
    showSuccess('Урок создан.')
    lessonCreateOpen.value = false
    await loadLessonsForModule(selectedModule.value.id)
  } catch (error) {
    console.error(error)
    showError('Не удалось создать урок.')
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

const deleteLesson = async (lesson) => {
  if (!selectedModule.value) {
    return
  }

  if (!window.confirm(`Удалить урок "${lesson.title}"?`)) {
    return
  }

  try {
    await store.deleteLesson(lesson.id, selectedModule.value.id)
    showSuccess('Урок удален.')
  } catch (error) {
    console.error(error)
    showError('Не удалось удалить урок.')
  }
}

const markLessonDirty = (lesson, patch) => {
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

  try {
    const updated = await store.updateLesson(editingLesson.value.id, patch, selectedModule.value.id)
    editingLesson.value = updated
    showSuccess('Урок обновлен.')
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
    showSuccess('Настройки квиза сохранены.')
  } catch (error) {
    console.error(error)
    showError('Не удалось сохранить настройки квиза.')
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
    showSuccess('Файл прикреплен.')
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

  try {
    const result = await store.uploadLessonVideo(editingLesson.value.id, file)
    editingVideoStatus.value = {
      status: result.status || 'pending',
      m3u8_url: '',
      error_message: '',
    }
    showSuccess('Видео загружено, началась обработка.')
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
    showSuccess('Вопрос удален.')
  } catch (error) {
    console.error(error)
    showError('Не удалось удалить вопрос.')
  }
}

const previewLesson = (lesson) => {
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
  <div class="mx-auto mt-8 max-w-7xl px-4">
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-3xl font-black text-slate-100">Конструктор курса</h1>
      <button
        class="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
        @click="regenerateFinalExam"
      >
        Сгенерировать финальный экзамен
      </button>
    </div>

    <div class="grid gap-6 lg:grid-cols-[320px,1fr]">
      <aside class="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-4">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold text-white">Модули курса</h2>
          <button class="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500" @click="openCreateModule">
            + Добавить модуль
          </button>
        </div>

        <div class="space-y-3">
          <div v-for="(module, index) in modules" :key="module.id" class="rounded-xl border border-slate-700 bg-slate-950/70">
            <div class="flex items-center gap-2 px-3 py-2">
              <button class="text-slate-400" @click="toggleModule(module.id)">
                {{ collapsedModules[module.id] ? '▶' : '▼' }}
              </button>

              <button class="flex-1 text-left text-sm font-semibold" :class="selectedModuleId === module.id ? 'text-indigo-300' : 'text-slate-200'" @click="selectModule(module.id)">
                {{ module.title }}
              </button>

              <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" :disabled="index === 0" @click="moveModule(module.id, -1)">↑</button>
              <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" :disabled="index === modules.length - 1" @click="moveModule(module.id, 1)">↓</button>
              <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" @click="openEditModule(module)">✎</button>
              <button class="rounded bg-rose-600 px-2 py-1 text-xs text-white" @click="deleteModule(module)">🗑</button>
            </div>

            <div v-if="!collapsedModules[module.id]" class="border-t border-slate-800 px-3 py-2">
              <div class="space-y-1 text-xs text-slate-400">
                <div v-for="lesson in store.lessonsByModule[module.id] || []" :key="lesson.id" class="truncate">
                  • {{ lesson.title }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <section class="rounded-2xl border border-slate-700/60 bg-slate-900/70 p-4">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-xl font-bold text-white">
            Уроки модуля: {{ selectedModule?.title || 'не выбран' }}
          </h2>
          <button class="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500" @click="openCreateLesson">
            + Добавить урок
          </button>
        </div>

        <div v-if="!selectedModule" class="rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-500">
          Выберите модуль в левой панели
        </div>

        <div v-else class="space-y-2">
          <div v-for="(lesson, index) in selectedLessons" :key="lesson.id" class="flex flex-wrap items-center gap-2 rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2">
            <span class="text-sm">
              {{ lesson.type === 'video' ? '🎬' : lesson.type === 'text' ? '📝' : lesson.type === 'quiz' ? '📊' : '🎓' }}
            </span>

            <input
              :value="lesson.title"
              class="min-w-[160px] flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
              @change="markLessonDirty(lesson, { title: $event.target.value })"
            >

            <label class="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-300">
              <input :checked="lesson.is_published" type="checkbox" @change="markLessonDirty(lesson, { is_published: $event.target.checked })">
              {{ lesson.is_published ? 'Опубликован' : 'Черновик' }}
            </label>

            <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" :disabled="index === 0" @click="moveLesson(lesson.id, -1)">↑</button>
            <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" :disabled="index === selectedLessons.length - 1" @click="moveLesson(lesson.id, 1)">↓</button>
            <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" @click="openEditLesson(lesson)">✏️</button>
            <button v-if="lesson.type === 'quiz' || lesson.type === 'final_exam'" class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" @click="openEditLesson(lesson)">⚙️</button>
            <button class="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200" @click="previewLesson(lesson)">👁️</button>
            <button class="rounded bg-rose-600 px-2 py-1 text-xs text-white" @click="deleteLesson(lesson)">🗑</button>
          </div>
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

    <div v-if="lessonCreateOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
      <div class="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <h3 class="text-xl font-bold text-white">Добавить урок</h3>

        <div class="mt-4 space-y-4">
          <div>
            <label class="mb-2 block text-sm text-slate-300">Название</label>
            <input v-model="lessonDraft.title" type="text" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
          </div>
          <div>
            <label class="mb-2 block text-sm text-slate-300">Тип урока</label>
            <select v-model="lessonDraft.type" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
              <option value="video">Видео</option>
              <option value="text">Текст</option>
              <option value="quiz">Тест</option>
              <option value="final_exam">Финальный экзамен</option>
            </select>
          </div>
          <div v-if="lessonDraft.type === 'video'">
            <label class="mb-2 block text-sm text-slate-300">YouTube URL</label>
            <input v-model="lessonDraft.video_url" type="text" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
          </div>
          <div>
            <label class="mb-2 block text-sm text-slate-300">Контент</label>
            <textarea v-model="lessonDraft.content" rows="5" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200"></textarea>
          </div>
          <label class="inline-flex items-center gap-2 text-sm text-slate-300">
            <input v-model="lessonDraft.is_published" type="checkbox">
            Опубликовать сразу
          </label>
        </div>

        <div class="mt-6 flex justify-end gap-2">
          <button class="rounded-xl bg-slate-800 px-4 py-2 text-sm text-slate-200" @click="lessonCreateOpen = false">Отмена</button>
          <button class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white" @click="submitCreateLesson">Создать</button>
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
