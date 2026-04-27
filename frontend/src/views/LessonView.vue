<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'

const API_BASE_URL = 'http://127.0.0.1:8000'

const route = useRoute()
const router = useRouter()

const lesson = ref(null)
const loading = ref(true)
const pageError = ref('')
const actionError = ref('')
const actionMessage = ref('')
const isCompleted = ref(false)
const actionLoading = ref(false)

const embedUrl = computed(() => {
  if (!lesson.value?.video_url) {
    return ''
  }

  const url = lesson.value.video_url
  let videoId = ''

  if (url.includes('watch?v=')) {
    videoId = url.split('watch?v=')[1].split('&')[0]
  } else if (url.includes('youtu.be/')) {
    videoId = url.split('youtu.be/')[1].split('?')[0]
  } else if (url.includes('embed/')) {
    return url
  }

  return videoId ? `https://www.youtube.com/embed/${videoId}` : ''
})

const fetchLesson = async () => {
  loading.value = true
  pageError.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const response = await api.get(`/lessons/${route.params.lessonId}/`)

    lesson.value = response.data
    isCompleted.value = Boolean(response.data.is_completed)
  } catch (error) {
    console.error('Ошибка загрузки урока:', error)
    pageError.value = 'Не удалось загрузить урок. Попробуйте открыть страницу еще раз.'
  } finally {
    loading.value = false
  }
}

const completeLesson = async () => {
  if (isCompleted.value || actionLoading.value) {
    return
  }

  actionLoading.value = true
  actionError.value = ''
  actionMessage.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const response = await axios.post(
      `${API_BASE_URL}/api/lessons/${route.params.lessonId}/complete/`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    )

    isCompleted.value = true
    actionMessage.value = response.data.course_completed
      ? 'Все уроки курса завершены. Чтобы подтвердить навыки, осталось успешно пройти Quiz.'
      : 'Урок сохранен как пройденный и добавлен в вашу активность.'
  } catch (error) {
    console.error('Ошибка завершения урока:', error)
    actionError.value =
      error.response?.data?.error || 'Не удалось отметить урок как пройденный. Попробуйте еще раз.'
  } finally {
    actionLoading.value = false
  }
}

onMounted(fetchLesson)
</script>

<template>
  <div v-if="loading" class="flex h-64 items-center justify-center text-slate-400">
    <div class="h-10 w-10 animate-spin rounded-full border-b-2 border-indigo-500"></div>
  </div>

  <div
    v-else-if="pageError"
    class="mx-auto mt-8 max-w-3xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="lesson" class="mx-auto mt-8 max-w-5xl px-4">
    <button
      class="group mb-6 flex items-center gap-2 font-medium text-slate-400 transition-colors hover:text-indigo-400"
      @click="router.back()"
    >
      <span class="transition-transform group-hover:-translate-x-1">←</span>
      Вернуться к программе
    </button>

    <div class="overflow-hidden rounded-3xl border border-slate-700/50 bg-slate-800/40 shadow-2xl">
      <div v-if="embedUrl" class="aspect-video bg-black shadow-inner">
        <iframe class="h-full w-full" :src="embedUrl" frameborder="0" allowfullscreen></iframe>
      </div>

      <div class="border-b border-slate-700/50 bg-slate-900/20 px-8 py-5">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.3em] text-indigo-300">Lesson Mode</p>
            <h1 class="mt-2 text-3xl font-bold text-slate-100">{{ lesson.title }}</h1>
          </div>

          <div
            class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold"
            :class="isCompleted
              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
              : 'border-slate-700 bg-slate-900/50 text-slate-300'"
          >
            <span>{{ isCompleted ? '✅' : '📘' }}</span>
            {{ isCompleted ? 'Урок уже пройден' : 'Материал еще не завершен' }}
          </div>
        </div>
      </div>

      <div class="p-8">
        <div class="prose prose-invert max-w-none whitespace-pre-wrap leading-relaxed text-slate-300">
          {{ lesson.content }}
        </div>
      </div>

      <div class="border-t border-slate-700/50 bg-slate-900/20 p-8">
        <div class="mx-auto max-w-2xl text-center">
          <button
            class="inline-flex items-center justify-center gap-3 rounded-2xl px-10 py-4 font-bold text-white transition-all"
            :class="isCompleted
              ? 'cursor-default bg-emerald-600/80'
              : 'bg-indigo-600 shadow-lg shadow-indigo-600/20 hover:bg-indigo-500'"
            :disabled="isCompleted || actionLoading"
            @click="completeLesson"
          >
            <span v-if="actionLoading">⏳</span>
            <span v-else-if="isCompleted">✅</span>
            <span v-else>✅</span>
            {{ isCompleted ? 'Пройдено' : actionLoading ? 'Сохраняем...' : 'Завершить урок' }}
          </button>

          <p class="mt-4 text-sm text-slate-500">
            Завершенные уроки попадают в активность профиля и влияют на прогресс изучаемых навыков.
          </p>

          <div
            v-if="actionMessage"
            class="mt-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-300"
          >
            {{ actionMessage }}
          </div>

          <div
            v-if="actionError"
            class="mt-5 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-300"
          >
            {{ actionError }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
