<script setup>
import { computed, reactive, ref, watch } from 'vue'

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
const videoSource = ref('youtube')

const isQuizType = computed(() => props.lesson?.type === 'quiz' || props.lesson?.type === 'final_exam')
const isVideoType = computed(() => props.lesson?.type === 'video')
const isTextType = computed(() => props.lesson?.type === 'text')
const isFinalExamType = computed(() => props.lesson?.type === 'final_exam')

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
  },
  { immediate: true, deep: true }
)

const saveLesson = () => {
  emit('save', {
    title: form.title,
    content: form.content,
    video_url: form.video_url,
    is_published: form.is_published,
  })
}

const addChoice = () => {
  newQuestion.choices.push({ text: '', is_correct: false })
}

const removeChoice = (index) => {
  if (newQuestion.choices.length <= 2) {
    return
  }
  newQuestion.choices.splice(index, 1)
}

const submitNewQuestion = () => {
  if (!newQuestion.text.trim()) {
    return
  }

  emit('create-question', {
    text: newQuestion.text,
    is_multiple: newQuestion.is_multiple,
    explanation: newQuestion.explanation,
    choices: newQuestion.choices.map((item) => ({
      text: item.text,
      is_correct: item.is_correct,
    })),
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
  if (attachmentFile.value) {
    emit('upload-attachment', attachmentFile.value)
  }
}

const chooseVideoFile = (event) => {
  const file = event.target.files?.[0] || null
  if (file) {
    emit('upload-video', file)
  }
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 p-4">
    <div class="mx-auto w-full max-w-4xl rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-2xl font-bold text-white">Редактор урока</h3>
          <p class="mt-1 text-sm text-slate-400">Тип: {{ lesson?.type }}</p>
        </div>
        <button class="rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-200" @click="emit('close')">Закрыть</button>
      </div>

      <div class="mt-6 grid gap-4 md:grid-cols-2">
        <div class="md:col-span-2">
          <label class="mb-2 block text-sm text-slate-300">Название урока</label>
          <input v-model="form.title" type="text" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
        </div>

        <label class="inline-flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-300 md:col-span-2">
          <input v-model="form.is_published" type="checkbox">
          Опубликован
        </label>

        <div v-if="isVideoType" class="md:col-span-2">
          <div class="mb-2 flex items-center gap-2">
            <button
              class="rounded-lg px-3 py-2 text-xs font-semibold"
              :class="videoSource === 'youtube' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'"
              @click="videoSource = 'youtube'"
            >
              Ссылка YouTube
            </button>
            <button
              class="rounded-lg px-3 py-2 text-xs font-semibold"
              :class="videoSource === 'file' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'"
              @click="videoSource = 'file'"
            >
              Загрузить файл
            </button>
          </div>

          <div v-if="videoSource === 'youtube'">
            <label class="mb-2 block text-sm text-slate-300">Ссылка на видео</label>
            <input v-model="form.video_url" type="text" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200" placeholder="YouTube URL">
          </div>

          <div v-else class="space-y-3 rounded-xl border border-slate-700 bg-slate-950 p-4">
            <label class="cursor-pointer rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500">
              Выбрать видеофайл
              <input type="file" accept="video/*" class="hidden" @change="chooseVideoFile">
            </label>
            <p class="text-xs text-slate-400">
              После загрузки видео будет обработано в HLS.
            </p>
            <p v-if="videoStatus?.status" class="text-xs text-slate-300">
              Статус: <span class="font-semibold">{{ videoStatus.status }}</span>
            </p>
            <p v-if="videoStatus?.error_message" class="text-xs text-rose-300">
              {{ videoStatus.error_message }}
            </p>
          </div>
        </div>

        <div v-if="isVideoType || isTextType" class="md:col-span-2">
          <label class="mb-2 block text-sm text-slate-300">Контент</label>
          <textarea v-model="form.content" rows="8" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200"></textarea>
        </div>
      </div>

      <div class="mt-6 rounded-xl border border-slate-700 bg-slate-950/70 p-4">
        <div class="flex items-center justify-between gap-2">
          <h4 class="text-lg font-semibold text-white">Материалы к уроку</h4>
          <label class="cursor-pointer rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500">
            + Добавить файл
            <input type="file" class="hidden" @change="chooseAttachment">
          </label>
        </div>

        <ul class="mt-4 space-y-2">
          <li v-for="file in attachments" :key="file.id" class="flex items-center justify-between rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200">
            <span class="truncate">{{ file.original_name }} ({{ Math.round((file.size || 0) / 1024) }} KB)</span>
            <button class="rounded-md bg-rose-600 px-2 py-1 text-xs text-white" @click="emit('delete-attachment', file)">Удалить</button>
          </li>
        </ul>
      </div>

      <div v-if="isQuizType" class="mt-6 rounded-xl border border-slate-700 bg-slate-950/70 p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="text-lg font-semibold text-white">Вопросы</h4>
          <div class="flex gap-2">
            <button class="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-500" @click="emit('open-quiz-config')">⚙ Настройки квиза</button>
            <button v-if="isFinalExamType" class="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500" @click="emit('regenerate-final-exam')">Перегенерировать</button>
          </div>
        </div>

        <div class="mt-4 space-y-3">
          <div v-for="question in questions" :key="question.id" class="rounded-xl border border-slate-700 bg-slate-900 p-3">
            <textarea
              :value="question.text"
              rows="2"
              class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              @change="emit('update-question', question, { ...question, text: $event.target.value })"
            ></textarea>
            <div class="mt-2 flex justify-end">
              <button class="rounded-md bg-rose-600 px-2 py-1 text-xs text-white" @click="emit('delete-question', question)">Удалить вопрос</button>
            </div>
          </div>

          <div class="rounded-xl border border-dashed border-slate-700 bg-slate-900/60 p-3">
            <h5 class="text-sm font-semibold text-slate-200">Добавить вопрос</h5>
            <textarea v-model="newQuestion.text" rows="2" class="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200" placeholder="Текст вопроса"></textarea>
            <label class="mt-2 inline-flex items-center gap-2 text-xs text-slate-300">
              <input v-model="newQuestion.is_multiple" type="checkbox">
              Несколько правильных ответов
            </label>
            <div class="mt-3 space-y-2">
              <div v-for="(choice, index) in newQuestion.choices" :key="index" class="flex items-center gap-2">
                <input v-model="choice.is_correct" type="checkbox">
                <input v-model="choice.text" type="text" class="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200" placeholder="Вариант ответа">
                <button class="rounded-md bg-slate-700 px-2 py-1 text-xs text-white" @click="removeChoice(index)">−</button>
              </div>
            </div>
            <div class="mt-3 flex gap-2">
              <button class="rounded-md bg-slate-700 px-2 py-1 text-xs text-white" @click="addChoice">+ Вариант</button>
              <button class="rounded-md bg-indigo-600 px-2 py-1 text-xs text-white" @click="submitNewQuestion">Добавить вопрос</button>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-6 flex justify-end">
        <button class="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500" @click="saveLesson">Сохранить изменения</button>
      </div>
    </div>
  </div>
</template>
