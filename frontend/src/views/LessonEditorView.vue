<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { showError, showSuccess } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const lessons = ref([])
const loading = ref(true)

// Состояние загрузки (чтобы блокировать кнопку)
const isUploading = ref(false)

// Переключатель источника видео
const videoSource = ref('youtube') // 'youtube' или 'file'
const videoFile = ref(null)

const newLesson = ref({
  title: '',
  video_url: '',
  content: '',
  order: 1
})

const fetchLessons = async () => {
  try {
    const response = await api.get(`/teacher/courses/${route.params.id}/lessons/`)
    lessons.value = response.data
    newLesson.value.order = lessons.value.length + 1
  } catch (error) {
    console.error('Ошибка загрузки уроков:', error)
  } finally {
    loading.value = false
  }
}

// Обработчик выбора файла
const handleFileUpload = (event) => {
  videoFile.value = event.target.files[0]
}

const addLesson = async () => {
  try {
    isUploading.value = true

    const payload = {
      title: newLesson.value.title,
      content: newLesson.value.content,
      order: newLesson.value.order,
      video_url: videoSource.value === 'youtube' ? newLesson.value.video_url : ''
    }

    const response = await api.post(`/teacher/courses/${route.params.id}/lessons/`, payload)
    const createdLesson = response.data

   if (videoSource.value === 'file' && videoFile.value) {
  showSuccess('Урок создан. Начинаем загрузку видео...')
  const formData = new FormData()
  formData.append('video', videoFile.value)   // ✅ поменяли имя

  await api.post(`/lessons/${createdLesson.id}/upload-video/`, formData)
  showSuccess('Видео загружено и отправлено на обработку (HLS)!')
} else {
      showSuccess('Урок успешно добавлен.')
    }

    // Очистка формы...
    newLesson.value = { title: '', video_url: '', content: '', order: lessons.value.length + 2 }
    videoSource.value = 'youtube'
    videoFile.value = null
    const fileInput = document.getElementById('video_file_input')
    if (fileInput) fileInput.value = ''
    await fetchLessons()

  } catch (error) {
    console.error('Ошибка:', error)
    const errorMsg = error.response?.data?.error || error.response?.data?.detail || 'Ошибка при добавлении урока'
    showError(errorMsg)
  } finally {
    isUploading.value = false
  }
}

onMounted(fetchLessons)
</script>

<template>
  <div class="max-w-6xl mx-auto mt-8 px-4">
    <button @click="router.back()"
      class="mb-8 text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-2 font-bold">
      ← Назад в кабинет
    </button>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
      <div class="lg:col-span-1">
        <h2 class="text-2xl font-black text-slate-100 mb-6">Программа курса</h2>
        <div v-if="loading" class="text-slate-600">Загрузка...</div>
        <div v-else-if="lessons.length === 0"
          class="p-8 border-2 border-dashed border-slate-800 rounded-3xl text-center text-slate-600 text-sm">
          Уроков пока нет. Создайте первый!
        </div>
        <div v-else class="space-y-3">
          <div v-for="lesson in lessons" :key="lesson.id"
            class="p-4 bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-2xl flex items-center gap-4 group hover:border-indigo-500/30 transition-all">
            <div
              class="w-8 h-8 rounded-lg bg-slate-700 text-slate-400 flex items-center justify-center font-bold text-xs group-hover:bg-indigo-500 group-hover:text-white transition-colors">
              {{ lesson.order }}
            </div>
            <div class="truncate">
              <p class="text-slate-200 font-bold text-sm truncate">{{ lesson.title }}</p>
              <p class="text-slate-500 text-[10px] uppercase tracking-tighter">Видео-лекция</p>
            </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2">
        <div class="bg-slate-800/20 backdrop-blur-xl p-8 rounded-[2rem] border border-slate-700/50 shadow-2xl">
          <h2 class="text-2xl font-black text-slate-100 mb-8">Добавить новый материал</h2>

          <form @submit.prevent="addLesson" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div class="md:col-span-3">
                <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Заголовок урока</label>
                <input v-model="newLesson.title" type="text" required
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                  placeholder="Напр: Введение в типы данных">
              </div>
              <div class="md:col-span-1">
                <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Порядок</label>
                <input v-model="newLesson.order" type="number" required
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100">
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-3 ml-1">Источник видео</label>
              <div class="flex flex-wrap gap-4 mb-4 bg-slate-900/30 p-2 rounded-2xl border border-slate-800/60 w-fit">
                <label class="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-xl transition-all"
                  :class="videoSource === 'youtube' ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-400 hover:text-slate-200'">
                  <input type="radio" v-model="videoSource" value="youtube" class="hidden">
                  <span class="text-sm font-bold">YouTube Ссылка</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer px-4 py-2 rounded-xl transition-all"
                  :class="videoSource === 'file' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-slate-200'">
                  <input type="radio" v-model="videoSource" value="file" class="hidden">
                  <span class="text-sm font-bold">Загрузить файл (HLS)</span>
                </label>
              </div>

              <div v-if="videoSource === 'youtube'">
                <input v-model="newLesson.video_url" type="url"
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                  placeholder="https://www.youtube.com/watch?v=...">
              </div>

              <div v-if="videoSource === 'file'">
                <input type="file" id="video_file_input" accept="video/mp4,video/x-m4v,video/*"
                  @change="handleFileUpload"
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-emerald-500 outline-none text-slate-100
                         file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-emerald-500/10 file:text-emerald-400 hover:file:bg-emerald-500/20 cursor-pointer">
                <p class="mt-2 text-xs text-slate-500 ml-1">Видео будет нарезано на сегменты HLS (1080p, 720p, 480p) в
                  фоновом режиме.</p>
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Текстовое содержание</label>
              <textarea v-model="newLesson.content" rows="6" required
                class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                placeholder="Развернутый текст урока, инструкции или конспект..."></textarea>
            </div>

            <button type="submit" :disabled="isUploading"
              class="w-full py-5 text-white font-black rounded-2xl transition-all shadow-xl text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              :class="videoSource === 'file' ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20' : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/20'">
              <span v-if="isUploading" class="flex items-center justify-center gap-2">
                <svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none"
                  viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                  </path>
                </svg>
                Загрузка...
              </span>
              <span v-else>
                Опубликовать урок
              </span>
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>