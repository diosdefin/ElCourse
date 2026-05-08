<script setup>
import Hls from 'hls.js'
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { showError, showSuccess } from '../utils/toast'

const route = useRoute()
const router = useRouter()

const lesson = ref(null)
const loading = ref(true)
const pageError = ref('')
const actionError = ref('')
const actionMessage = ref('')
const isCompleted = ref(false)
const actionLoading = ref(false)

const manifestLoading = ref(true)
const manifestState = ref('pending')
const manifestUrl = ref('')
const manifestError = ref('')
const useLegacyPlayer = ref(false)

const videoElement = ref(null)
const hlsInstance = ref(null)
const availableLevels = ref([])
const selectedLevel = ref(-1)

const resumePromptVisible = ref(false)
const savedWatchedSeconds = ref(0)
const lastSyncedSeconds = ref(0)

let progressSyncTimer = null
let manifestPollTimer = null

const isAuthenticated = computed(() => Boolean(localStorage.getItem('access_token')))
const isPreviewMode = computed(() => route.query.preview === '1')
const isManifestProcessing = computed(
  () => manifestState.value === 'pending' || manifestState.value === 'processing'
)
const legacyVideoUrl = computed(() => lesson.value?.video_url || '')

const legacyEmbedUrl = computed(() => {
  const url = legacyVideoUrl.value
  if (!url) {
    return ''
  }

  try {
    const parsed = new URL(url)
    if (parsed.hostname.includes('youtu.be')) {
      const videoId = parsed.pathname.replace('/', '')
      return videoId ? `https://www.youtube.com/embed/${videoId}` : ''
    }
    if (parsed.hostname.includes('youtube.com')) {
      const videoId = parsed.searchParams.get('v')
      if (videoId) {
        return `https://www.youtube.com/embed/${videoId}`
      }
      if (parsed.pathname.includes('/embed/')) {
        return url
      }
    }
  } catch (error) {
    console.debug('Видео не удалось распознать как URL YouTube:', error)
  }

  return ''
})

const showLegacyVideo = computed(
  () => isAuthenticated.value && useLegacyPlayer.value && Boolean(legacyVideoUrl.value)
)

const savedTimeLabel = computed(() => {
  const total = savedWatchedSeconds.value
  const minutes = Math.floor(total / 60)
  const seconds = `${total % 60}`.padStart(2, '0')
  return `${minutes}:${seconds}`
})

const qualityOptions = computed(() => {
  const options = [{ value: -1, label: 'Auto' }]
  for (const level of availableLevels.value) {
    options.push({ value: level.index, label: level.label })
  }
  return options
})

const clearManifestPolling = () => {
  if (manifestPollTimer) {
    window.clearInterval(manifestPollTimer)
    manifestPollTimer = null
  }
}

const clearProgressSync = async () => {
  if (progressSyncTimer) {
    window.clearInterval(progressSyncTimer)
    progressSyncTimer = null
  }
  if (!isPreviewMode.value) {
    await saveWatchProgress(true)
  }
}

const teardownPlayer = () => {
  if (hlsInstance.value) {
    hlsInstance.value.destroy()
    hlsInstance.value = null
  }
  if (videoElement.value) {
    videoElement.value.removeAttribute('src')
    videoElement.value.load()
  }
}

const fetchLesson = async () => {
  loading.value = true
  pageError.value = ''

  try {
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

const setupManifestPolling = () => {
  if (manifestPollTimer) {
    return
  }

  manifestPollTimer = window.setInterval(async () => {
    await fetchManifest({ keepLoading: true })
  }, 8000)
}

const fetchWatchProgress = async () => {
  if (!isAuthenticated.value || isPreviewMode.value) {
    return
  }

  try {
    const response = await api.get(`/lessons/${route.params.lessonId}/progress/`)
    const watchedSeconds = Number(response.data.watched_seconds || 0)
    lastSyncedSeconds.value = watchedSeconds
    if (watchedSeconds > 0) {
      savedWatchedSeconds.value = watchedSeconds
      resumePromptVisible.value = true
    }
  } catch (error) {
    console.error('Ошибка загрузки прогресса просмотра:', error)
  }
}

const saveWatchProgress = async (force = false) => {
  if (!isAuthenticated.value || isPreviewMode.value || !videoElement.value) {
    return
  }

  const currentSeconds = Math.floor(videoElement.value.currentTime || 0)
  if (currentSeconds <= 0) {
    return
  }

  if (!force && Math.abs(currentSeconds - lastSyncedSeconds.value) < 8) {
    return
  }

  try {
    await api.patch(`/lessons/${route.params.lessonId}/progress/`, {
      watched_seconds: currentSeconds,
    })
    lastSyncedSeconds.value = currentSeconds
  } catch (error) {
    console.error('Ошибка сохранения прогресса просмотра:', error)
  }
}

const startProgressSync = () => {
  if (!isAuthenticated.value || isPreviewMode.value) {
    return
  }

  if (progressSyncTimer) {
    window.clearInterval(progressSyncTimer)
  }

  progressSyncTimer = window.setInterval(() => {
    saveWatchProgress(false)
  }, 10000)
}

const jumpToSavedTime = () => {
  if (!videoElement.value || !savedWatchedSeconds.value) {
    resumePromptVisible.value = false
    return
  }

  videoElement.value.currentTime = savedWatchedSeconds.value
  resumePromptVisible.value = false
  showSuccess(`Продолжаем с ${savedTimeLabel.value}`)
}

const startFromBeginning = () => {
  resumePromptVisible.value = false
}

const applyQuality = () => {
  if (hlsInstance.value) {
    hlsInstance.value.currentLevel = Number(selectedLevel.value)
  }
}

const initPlayer = async () => {
  await nextTick()

  if (!videoElement.value || !manifestUrl.value) {
    console.log('[LessonView] initPlayer skipped', {
      hasVideoElement: Boolean(videoElement.value),
      manifestUrl: manifestUrl.value,
      manifestState: manifestState.value,
      manifestLoading: manifestLoading.value,
      isManifestProcessing: isManifestProcessing.value,
    })
    return
  }

  teardownPlayer()
  availableLevels.value = []
  selectedLevel.value = -1

  const video = videoElement.value
  console.log('[LessonView] initPlayer start', {
    manifestUrl: manifestUrl.value,
    hlsSupported: Hls.isSupported(),
    nativeHlsSupported: video.canPlayType('application/vnd.apple.mpegurl'),
  })

  if (Hls.isSupported()) {
    const hls = new Hls({
      enableWorker: true,
      capLevelToPlayerSize: true,
      lowLatencyMode: false,
    })
    hlsInstance.value = hls
    hls.attachMedia(video)

    hls.on(Hls.Events.MEDIA_ATTACHED, () => {
      console.log('[LessonView] HLS media attached')
      hls.loadSource(manifestUrl.value)
    })

    hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
      console.log('[LessonView] HLS manifest parsed', { levels: data.levels.length })
      availableLevels.value = data.levels.map((level, index) => ({
        index,
        label: level.height ? `${level.height}p` : `Level ${index + 1}`,
      }))
      selectedLevel.value = -1
      startProgressSync()
    })

    hls.on(Hls.Events.ERROR, (_, data) => {
      console.log('[LessonView] HLS error', data)
      if (data.fatal) {
        manifestError.value = 'Не удалось воспроизвести видео. Попробуйте обновить страницу.'
      }
    })
  } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    console.log('[LessonView] using native HLS playback')
    video.src = manifestUrl.value
    video.addEventListener(
      'loadedmetadata',
      () => {
        startProgressSync()
      },
      { once: true }
    )
  } else {
    manifestError.value = 'Ваш браузер не поддерживает HLS-видео.'
  }

  await fetchWatchProgress()
}

const fetchManifest = async ({ keepLoading = false } = {}) => {
  if (!isAuthenticated.value) {
    manifestLoading.value = false
    manifestState.value = 'pending'
    return
  }

  if (!keepLoading) {
    manifestLoading.value = true
  }
  manifestError.value = ''

  try {
    const response = await api.get(`/lessons/${route.params.lessonId}/video/manifest/`)
    console.log('[LessonView] manifest response', response.data)

    manifestState.value = response.data.status || 'pending'
    manifestUrl.value = response.data.m3u8_url || ''
    useLegacyPlayer.value = false

    console.log('[LessonView] manifest state updated', {
      manifestState: manifestState.value,
      manifestUrl: manifestUrl.value,
      manifestLoading: manifestLoading.value,
      isManifestProcessing: isManifestProcessing.value,
    })

    if (manifestState.value === 'ready' && manifestUrl.value) {
      clearManifestPolling()
      manifestLoading.value = false
      await nextTick()
      await initPlayer()
    } else if (manifestState.value === 'failed') {
      clearManifestPolling()
      if (legacyVideoUrl.value) {
        useLegacyPlayer.value = true
      } else {
        manifestError.value = response.data.error_message || 'Ошибка обработки видео.'
      }
    } else if (manifestState.value === 'pending' && legacyVideoUrl.value && !manifestUrl.value) {
      clearManifestPolling()
      useLegacyPlayer.value = true
    } else if (isManifestProcessing.value) {
      setupManifestPolling()
    }
  } catch (error) {
    console.error('Ошибка запроса манифеста:', error)
    if (legacyVideoUrl.value) {
      useLegacyPlayer.value = true
    } else {
      manifestError.value = 'Не удалось получить статус видео.'
    }
  } finally {
    if (!keepLoading && manifestState.value !== 'ready') {
      manifestLoading.value = false
    }
  }
}

const completeLesson = async () => {
  if (isPreviewMode.value) {
    return
  }

  if (isCompleted.value || actionLoading.value) {
    return
  }

  actionLoading.value = true
  actionError.value = ''
  actionMessage.value = ''

  try {
    const response = await api.post(`/lessons/${route.params.lessonId}/complete/`, {})

    isCompleted.value = true
    actionMessage.value = response.data.course_completed
      ? 'Все уроки курса завершены. Чтобы подтвердить навыки, осталось успешно пройти Quiz.'
      : 'Урок отмечен как пройденный и добавлен в вашу активность.'
    showSuccess('Урок отмечен как пройденный.')
  } catch (error) {
    console.error('Ошибка завершения урока:', error)
    actionError.value =
      error.response?.data?.error || 'Не удалось отметить урок как пройденный. Попробуйте еще раз.'
    showError(actionError.value)
  } finally {
    actionLoading.value = false
  }
}

onMounted(async () => {
  await fetchLesson()
  await fetchManifest()
})

onUnmounted(async () => {
  clearManifestPolling()
  await clearProgressSync()
  teardownPlayer()
})
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
      <div class="aspect-video bg-black">
        <div
          v-if="!isAuthenticated"
          class="flex h-full items-center justify-center bg-slate-950/90 px-6 text-center text-slate-400"
        >
          Войдите в аккаунт, чтобы смотреть видеоурок.
        </div>

        <div
          v-else-if="manifestLoading || isManifestProcessing"
          class="flex h-full items-center justify-center bg-slate-950/90"
        >
          <div class="space-y-4 text-center">
            <div class="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-emerald-500"></div>
            <p class="text-sm font-medium text-slate-300">Видео обрабатывается, подождите немного...</p>
          </div>
        </div>

        <div
          v-else-if="manifestError"
          class="flex h-full items-center justify-center bg-slate-950/90 px-6 text-center text-rose-300"
        >
          {{ manifestError }}
        </div>

        <iframe
          v-else-if="showLegacyVideo && legacyEmbedUrl"
          class="h-full w-full"
          :src="legacyEmbedUrl"
          title="Lesson video"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen
        ></iframe>

        <video
          v-else-if="showLegacyVideo && !legacyEmbedUrl"
          class="h-full w-full"
          :src="legacyVideoUrl"
          controls
          preload="metadata"
        ></video>

        <video
          v-else
          ref="videoElement"
          class="h-full w-full"
          controls
          preload="metadata"
        ></video>
      </div>

      <div class="border-b border-slate-700/50 bg-slate-900/20 px-8 py-5">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.3em] text-indigo-300">Lesson Mode</p>
            <h1 class="mt-2 text-3xl font-bold text-slate-100">{{ lesson.title }}</h1>
          </div>

          <div class="flex items-center gap-3">
            <select
              v-if="availableLevels.length > 0"
              v-model.number="selectedLevel"
              class="rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-sm font-semibold text-slate-200 outline-none focus:border-indigo-400"
              @change="applyQuality"
            >
              <option v-for="option in qualityOptions" :key="option.value" :value="option.value">
                Качество: {{ option.label }}
              </option>
            </select>

            <div
              class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold"
              :class="isCompleted
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                : 'border-slate-700 bg-slate-900/50 text-slate-300'"
            >
              <span>{{ isCompleted ? '✓' : '•' }}</span>
              {{ isCompleted ? 'Урок уже пройден' : 'Материал еще не завершен' }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="resumePromptVisible" class="border-b border-slate-700/50 bg-emerald-500/10 px-8 py-5">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-sm text-emerald-200">
            Продолжить с остановленного места ({{ savedTimeLabel }})?
          </p>
          <div class="flex gap-2">
            <button
              class="rounded-xl border border-emerald-400/30 bg-emerald-500/20 px-4 py-2 text-sm font-bold text-emerald-200 transition hover:bg-emerald-500/30"
              @click="jumpToSavedTime"
            >
              Продолжить
            </button>
            <button
              class="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-slate-500"
              @click="startFromBeginning"
            >
              С начала
            </button>
          </div>
        </div>
      </div>

      <div class="p-8">
        <div class="prose prose-invert max-w-none whitespace-pre-wrap leading-relaxed text-slate-300">
          {{ lesson.content || 'Контент урока доступен после входа в систему.' }}
        </div>
      </div>

      <div v-if="!isPreviewMode" class="border-t border-slate-700/50 bg-slate-900/20 p-8">
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
            <span v-else-if="isCompleted">✓</span>
            <span v-else>✓</span>
            {{ isCompleted ? 'Пройдено' : actionLoading ? 'Сохраняем...' : 'Завершить урок' }}
          </button>

          <p class="mt-4 text-sm text-slate-500">
            Прогресс просмотра сохраняется автоматически каждые 10 секунд.
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

      <div v-else class="border-t border-slate-700/50 bg-slate-900/20 p-6 text-center text-sm text-slate-400">
        Preview mode: progress tracking and lesson completion are disabled.
      </div>
    </div>
  </div>
</template>
