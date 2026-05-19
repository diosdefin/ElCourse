<script setup>
import DOMPurify from 'dompurify'
import Hls from 'hls.js'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'
import { showError, showSuccess } from '../utils/toast'

const props = defineProps({
  lessonId: {
    type: [Number, String],
    default: null,
  },
  embedded: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['lesson-updated'])

const route = useRoute()
const router = useRouter()

const lesson = ref(null)
const loading = ref(true)
const pageError = ref('')
const actionError = ref('')
const actionMessage = ref('')
const actionLoading = ref(false)
const isCompleted = ref(false)

const attachments = ref([])
const attachmentsLoading = ref(false)

const manifestLoading = ref(false)
const manifestState = ref('pending')
const manifestUrl = ref('')
const manifestError = ref('')
const playbackNotice = ref('')
const useLegacyPlayer = ref(false)

const videoElement = ref(null)
const hlsInstance = ref(null)
const availableLevels = ref([])
const selectedLevel = ref(-1)

const resumePromptVisible = ref(false)
const savedWatchedSeconds = ref(0)
const lastSyncedSeconds = ref(0)

const quizLoading = ref(false)
const quizError = ref('')
const quizData = ref(null)
const quizResult = ref(null)
const quizAnswers = ref({})
const quizSubmitting = ref(false)
const timerSecondsLeft = ref(0)
let timerInterval = null

let progressSyncTimer = null
let manifestPollTimer = null

const resolvedLessonId = computed(() => props.lessonId || route.params.lessonId)
const isAuthenticated = computed(() => Boolean(localStorage.getItem('access_token')))
const isPreviewMode = computed(() => route.query.preview === '1')
const isManifestProcessing = computed(() => manifestState.value === 'pending' || manifestState.value === 'processing')

const isVideoLesson = computed(() => lesson.value?.type === 'video')
const isTextLesson = computed(() => lesson.value?.type === 'text')
const isQuizLesson = computed(() => lesson.value?.type === 'quiz' || lesson.value?.type === 'final_exam')

const cleanHtmlContent = computed(() => {
  const dirty = lesson.value?.content || ''
  return DOMPurify.sanitize(dirty)
})

const lessonTypeLabel = computed(() => {
  if (lesson.value?.type === 'video') return 'Видео'
  if (lesson.value?.type === 'text') return 'Текстовый урок'
  if (lesson.value?.type === 'quiz') return 'Тест'
  if (lesson.value?.type === 'final_exam') return 'Финальный экзамен'
  return 'Урок'
})

const lessonHint = computed(() => {
  if (isVideoLesson.value) return 'Посмотрите видеоматериал, изучите конспект и отметьте урок завершённым.'
  if (isTextLesson.value) return 'Изучите материал урока и завершите его вручную.'
  if (lesson.value?.type === 'final_exam') return 'Итоговая проверка знаний по материалам курса.'
  if (isQuizLesson.value) return 'Ответьте на вопросы теста с учётом попыток и проходного балла.'
  return 'Изучите материал урока.'
})

const fallbackVideoUrl = computed(() => lesson.value?.fallback_video_url || lesson.value?.video_url || '')
const showLegacyVideo = computed(() => isAuthenticated.value && useLegacyPlayer.value && Boolean(fallbackVideoUrl.value))

const legacyEmbedUrl = computed(() => {
  const url = fallbackVideoUrl.value
  if (!url) return ''

  try {
    const parsed = new URL(url)
    if (parsed.hostname.includes('youtu.be')) {
      const videoId = parsed.pathname.replace('/', '')
      return videoId ? `https://www.youtube.com/embed/${videoId}` : ''
    }
    if (parsed.hostname.includes('youtube.com')) {
      const videoId = parsed.searchParams.get('v')
      if (videoId) return `https://www.youtube.com/embed/${videoId}`
      if (parsed.pathname.includes('/embed/')) return url
    }
  } catch (error) {
  }

  return ''
})

const savedTimeLabel = computed(() => formatTime(savedWatchedSeconds.value))

const qualityOptions = computed(() => {
  const options = [{ value: -1, label: 'Авто' }]
  for (const level of availableLevels.value) {
    options.push({ value: level.index, label: level.label })
  }
  return options
})

const quizConfig = computed(() => quizData.value?.quiz_config || null)
const quizQuestions = computed(() => quizData.value?.questions || [])
const attemptsUsed = computed(() => quizResult.value?.attempts_used ?? quizData.value?.attempts_used ?? 0)
const maxAttempts = computed(() => quizConfig.value?.max_attempts ?? 0)
const blockedUntil = computed(() => quizResult.value?.blocked_until || quizData.value?.blocked_until || null)
const isBlocked = computed(() => {
  if (!blockedUntil.value) return false
  const until = new Date(blockedUntil.value).getTime()
  return Number.isFinite(until) && until > Date.now()
})
const hasTimeLimit = computed(() => Number(quizConfig.value?.time_limit_minutes || 0) > 0)
const isTimeExpired = computed(() => hasTimeLimit.value && timerSecondsLeft.value <= 0 && !quizResult.value)
const quizInputsDisabled = computed(() => isPreviewMode.value || isBlocked.value || isTimeExpired.value || quizSubmitting.value)

const answeredQuestionsCount = computed(() => {
  return quizQuestions.value.filter((question) => {
    const answer = quizAnswers.value[question.id]
    if (question.is_multiple) return Array.isArray(answer) && answer.length > 0
    return answer !== undefined && answer !== null && answer !== ''
  }).length
})
const allQuestionsAnswered = computed(() => quizQuestions.value.length > 0 && answeredQuestionsCount.value === quizQuestions.value.length)
const quizAnswerProgress = computed(() => {
  if (!quizQuestions.value.length) return 0
  return Math.round((answeredQuestionsCount.value / quizQuestions.value.length) * 100)
})

const canSubmitQuiz = computed(() => {
  if (isPreviewMode.value) return false
  if (isBlocked.value) return false
  if (isTimeExpired.value) return false
  if (!quizQuestions.value.length) return false
  if (!allQuestionsAnswered.value) return false
  return true
})

const formattedBlockedUntil = computed(() => {
  if (!blockedUntil.value) return ''
  const dateObj = new Date(blockedUntil.value)
  if (Number.isNaN(dateObj.getTime())) return blockedUntil.value
  return dateObj.toLocaleString('ru-RU')
})

const timerLabel = computed(() => formatTime(Math.max(0, timerSecondsLeft.value)))

function formatTime(totalSeconds) {
  const total = Math.max(0, Number(totalSeconds) || 0)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = `${total % 60}`.padStart(2, '0')

  if (hours > 0) {
    return `${hours}:${`${minutes}`.padStart(2, '0')}:${seconds}`
  }
  return `${minutes}:${seconds}`
}

function formatFileSize(bytes) {
  const size = Number(bytes || 0)
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  if (size >= 1024) return `${Math.round(size / 1024)} KB`
  return `${size} B`
}

const clearManifestPolling = () => {
  if (manifestPollTimer) {
    window.clearInterval(manifestPollTimer)
    manifestPollTimer = null
  }
}

const stopQuizTimer = () => {
  if (timerInterval) {
    window.clearInterval(timerInterval)
    timerInterval = null
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

const setupManifestPolling = () => {
  if (manifestPollTimer) return
  manifestPollTimer = window.setInterval(async () => {
    await fetchManifest({ keepLoading: true })
  }, 8000)
}

const fetchLesson = async () => {
  loading.value = true
  pageError.value = ''
  actionError.value = ''
  actionMessage.value = ''
  quizError.value = ''
  quizResult.value = null
  quizData.value = null
  quizAnswers.value = {}
  attachments.value = []
  resumePromptVisible.value = false
  savedWatchedSeconds.value = 0
  lastSyncedSeconds.value = 0

  try {
    const response = await api.get(`/lessons/${resolvedLessonId.value}/`)
    lesson.value = response.data
    isCompleted.value = Boolean(response.data.is_completed)
    manifestState.value = response.data?.hls_status || (response.data?.type === 'video' ? 'missing' : 'no_video')
    manifestUrl.value = response.data?.hls_manifest_url || ''
    manifestError.value = response.data?.hls_error || ''
  } catch (error) {
    console.error(error)
    pageError.value = error.response?.data?.detail || 'Не удалось загрузить урок.'
  } finally {
    loading.value = false
  }
}

const fetchAttachments = async () => {
  if (!resolvedLessonId.value) return
  attachmentsLoading.value = true
  try {
    const response = await api.get(`/lessons/${resolvedLessonId.value}/attachments/`)
    attachments.value = response.data
  } catch (error) {
    attachments.value = []
    console.error(error)
  } finally {
    attachmentsLoading.value = false
  }
}

const fetchWatchProgress = async () => {
  if (!isAuthenticated.value || isPreviewMode.value || !isVideoLesson.value) return

  try {
    const response = await api.get(`/lessons/${resolvedLessonId.value}/progress/`)
    const watchedSeconds = Number(response.data.watched_seconds || 0)
    lastSyncedSeconds.value = watchedSeconds
    if (watchedSeconds > 0) {
      savedWatchedSeconds.value = watchedSeconds
      resumePromptVisible.value = true
    }
  } catch (error) {
    console.error(error)
  }
}

const saveWatchProgress = async (force = false) => {
  if (!isAuthenticated.value || isPreviewMode.value || !isVideoLesson.value || !videoElement.value) return

  const currentSeconds = Math.floor(videoElement.value.currentTime || 0)
  if (currentSeconds <= 0) return
  if (!force && Math.abs(currentSeconds - lastSyncedSeconds.value) < 8) return

  try {
    await api.patch(`/lessons/${resolvedLessonId.value}/progress/`, {
      watched_seconds: currentSeconds,
    })
    lastSyncedSeconds.value = currentSeconds
  } catch (error) {
    console.error(error)
  }
}

const startProgressSync = () => {
  if (!isAuthenticated.value || isPreviewMode.value || !isVideoLesson.value) return

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
  showSuccess(`Продолжили с ${savedTimeLabel.value}.`)
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
  if (!isVideoLesson.value || !videoElement.value || !manifestUrl.value) return

  teardownPlayer()
  availableLevels.value = []
  selectedLevel.value = -1

  const video = videoElement.value

  if (Hls.isSupported()) {
    const hls = new Hls({
      enableWorker: true,
      capLevelToPlayerSize: true,
      lowLatencyMode: false,
    })
    hlsInstance.value = hls
    hls.attachMedia(video)

    hls.on(Hls.Events.MEDIA_ATTACHED, () => {
      hls.loadSource(manifestUrl.value)
    })

    hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
      availableLevels.value = data.levels.map((level, index) => ({
        index,
        label: level.height ? `${level.height}p` : `Поток ${index + 1}`,
      }))
      selectedLevel.value = -1
      startProgressSync()
    })

    hls.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) {
        manifestError.value = 'Не удалось воспроизвести HLS-поток.'
      }
    })
  } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = manifestUrl.value
    video.addEventListener(
      'loadedmetadata',
      () => {
        startProgressSync()
      },
      { once: true }
    )
  } else {
    manifestError.value = 'Браузер не поддерживает HLS-воспроизведение.'
  }

  await fetchWatchProgress()
}

const fetchManifest = async ({ keepLoading = false } = {}) => {
  if (!isVideoLesson.value) {
    manifestLoading.value = false
    manifestState.value = 'no_video'
    return
  }

  if (!isAuthenticated.value) {
    manifestLoading.value = false
    manifestState.value = 'pending'
    return
  }

  if (!keepLoading) {
    manifestLoading.value = true
  }
  manifestError.value = ''
  playbackNotice.value = ''

  try {
    const response = await api.get(`/lessons/${resolvedLessonId.value}/video/manifest/`)
    manifestState.value = response.data.status || 'missing'
    manifestUrl.value = response.data.manifest_url || response.data.m3u8_url || ''
    useLegacyPlayer.value = false

    if (manifestState.value === 'ready' && manifestUrl.value) {
      clearManifestPolling()
      manifestLoading.value = false
      await nextTick()
      await initPlayer()
    } else if (manifestState.value === 'missing') {
      clearManifestPolling()
      if (fallbackVideoUrl.value) {
        useLegacyPlayer.value = true
        playbackNotice.value = 'Using direct video without HLS.'
      } else {
        manifestError.value = response.data.message || 'HLS video is not uploaded for this lesson.'
      }
    } else if (manifestState.value === 'failed') {
      clearManifestPolling()
      if (fallbackVideoUrl.value) {
        useLegacyPlayer.value = true
        playbackNotice.value = 'Using direct video instead of HLS.'
      } else {
        manifestError.value = response.data.error_message || 'Video processing failed.'
      }
    } else if (manifestState.value === 'inconsistent') {
      clearManifestPolling()
      if (fallbackVideoUrl.value) {
        useLegacyPlayer.value = true
        playbackNotice.value = 'Using direct video because HLS state is inconsistent.'
      } else {
        manifestError.value = response.data.error_message || response.data.message || 'HLS state is inconsistent.'
      }
    } else if (isManifestProcessing.value) {
      setupManifestPolling()
    }
  } catch (error) {
    console.error(error)
    const payload = error.response?.data || {}
    const statusCode = error.response?.status

    if (statusCode === 409) {
      manifestState.value = payload.status || 'missing'
      manifestUrl.value = payload.manifest_url || payload.m3u8_url || ''
      useLegacyPlayer.value = false

      if (payload.playback_mode === 'fallback_video' && fallbackVideoUrl.value) {
        useLegacyPlayer.value = true
        playbackNotice.value = manifestState.value === 'failed'
          ? 'Using direct video instead of HLS.'
          : 'Using direct video without HLS.'
      } else {
        manifestError.value = payload.error_message || payload.message || 'Could not load video manifest.'
      }
    } else if (fallbackVideoUrl.value) {
      useLegacyPlayer.value = true
      playbackNotice.value = 'Using direct video.'
    } else {
      manifestError.value = 'Could not load video manifest.'
    }
  } finally {
    if (!keepLoading && manifestState.value !== 'ready') {
      manifestLoading.value = false
    }
  }
}

const completeLesson = async () => {
  if (isPreviewMode.value || isQuizLesson.value || isCompleted.value || actionLoading.value) return

  actionLoading.value = true
  actionError.value = ''
  actionMessage.value = ''

  try {
    const response = await api.post(`/lessons/${resolvedLessonId.value}/complete/`, {})
    isCompleted.value = true
    actionMessage.value = response.data.course_completed
      ? 'Все уроки курса завершены.'
      : 'Урок отмечен как завершённый.'
    showSuccess('Урок завершён.')
    emit('lesson-updated')
  } catch (error) {
    actionError.value = error.response?.data?.error || 'Не удалось завершить урок.'
    showError(actionError.value)
  } finally {
    actionLoading.value = false
  }
}

const loadQuiz = async (resetResult = true) => {
  if (!isQuizLesson.value) return

  quizLoading.value = true
  quizError.value = ''
  if (resetResult) {
    quizResult.value = null
  }
  stopQuizTimer()

  try {
    const response = await api.get(`/lessons/${resolvedLessonId.value}/quiz/`)
    quizData.value = response.data
    quizAnswers.value = {}

    const limitMinutes = Number(response.data?.quiz_config?.time_limit_minutes || 0)
    if (limitMinutes > 0 && !isPreviewMode.value && !isBlocked.value && !quizResult.value) {
      timerSecondsLeft.value = limitMinutes * 60
      timerInterval = window.setInterval(() => {
        timerSecondsLeft.value -= 1
        if (timerSecondsLeft.value <= 0) {
          timerSecondsLeft.value = 0
          stopQuizTimer()
          quizError.value = 'Время на прохождение теста истекло.'
        }
      }, 1000)
    } else {
      timerSecondsLeft.value = 0
    }
  } catch (error) {
    console.error(error)
    quizError.value = error.response?.data?.detail || 'Не удалось загрузить тест.'
  } finally {
    quizLoading.value = false
  }
}

const setSingleAnswer = (questionId, choiceId) => {
  quizAnswers.value[questionId] = choiceId
}

const toggleMultiAnswer = (questionId, choiceId) => {
  const existing = Array.isArray(quizAnswers.value[questionId]) ? [...quizAnswers.value[questionId]] : []
  const index = existing.indexOf(choiceId)
  if (index >= 0) {
    existing.splice(index, 1)
  } else {
    existing.push(choiceId)
  }
  quizAnswers.value[questionId] = existing
}

const isChoiceSelected = (question, choice) => {
  const answer = quizAnswers.value[question.id]
  if (question.is_multiple) {
    return Array.isArray(answer) && answer.includes(choice.id)
  }
  return answer === choice.id
}

const submitQuiz = async () => {
  if (!canSubmitQuiz.value || quizSubmitting.value) {
    if (!allQuestionsAnswered.value) showError('Ответьте на все вопросы перед отправкой.')
    return
  }

  quizSubmitting.value = true
  quizError.value = ''

  try {
    const payload = { answers: quizAnswers.value }
    const response = await api.post(`/lessons/${resolvedLessonId.value}/quiz/submit/`, payload)
    quizResult.value = response.data
    stopQuizTimer()
    if (response.data.is_passed) {
      isCompleted.value = true
      showSuccess('Тест успешно пройден.')
      emit('lesson-updated')
    } else {
      showError('Тест не пройден. Изучите ошибки и попробуйте снова.')
    }
    await loadQuiz(false)
  } catch (error) {
    console.error(error)
    quizError.value = error.response?.data?.detail || 'Не удалось отправить ответы.'
  } finally {
    quizSubmitting.value = false
  }
}

const loadAll = async () => {
  clearManifestPolling()
  stopQuizTimer()
  await clearProgressSync()
  teardownPlayer()

  await fetchLesson()
  if (!lesson.value) return

  await fetchAttachments()
  if (isVideoLesson.value) {
    await fetchManifest()
  } else {
    manifestLoading.value = false
    manifestState.value = 'ready'
  }
  if (isQuizLesson.value) {
    await loadQuiz()
  }
}

watch(resolvedLessonId, async (newValue, oldValue) => {
  if (!newValue || newValue === oldValue) return
  await loadAll()
})

onMounted(loadAll)

onUnmounted(async () => {
  clearManifestPolling()
  stopQuizTimer()
  await clearProgressSync()
  teardownPlayer()
})
</script>

<template>
  <div v-if="loading" class="flex min-h-[420px] items-center justify-center text-slate-400">
    <div class="rounded-3xl border border-slate-800 bg-slate-950/40 px-8 py-7 text-center">
      <div class="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-400"></div>
      <p class="mt-4 text-sm font-medium">Загрузка урока...</p>
    </div>
  </div>

  <div
    v-else-if="pageError"
    class="mx-auto mt-8 max-w-3xl rounded-3xl border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
  >
    {{ pageError }}
  </div>

  <div v-else-if="lesson" :class="embedded ? 'min-w-0' : 'mx-auto mt-4 max-w-5xl px-0 sm:mt-8 sm:px-4'">
    <button
      v-if="!embedded"
      class="group mb-6 inline-flex items-center gap-2 rounded-xl border border-slate-700/70 bg-slate-900/70 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-indigo-400/60 hover:text-white"
      @click="router.back()"
    >
      <svg class="h-4 w-4 transition-transform group-hover:-translate-x-0.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      Назад
    </button>

    <article class="min-w-0 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/20 shadow-2xl shadow-slate-950/20">
      <section v-if="isVideoLesson" class="relative aspect-video max-w-full overflow-hidden bg-black">
        <div
          v-if="!isAuthenticated"
          class="flex h-full items-center justify-center bg-slate-950/95 px-4 text-center text-slate-400 sm:px-6"
        >
          <div>
            <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-slate-500">
              <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M7 10V8a5 5 0 0110 0v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                <path d="M6 10h12v10H6V10z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
              </svg>
            </div>
            <p class="font-semibold text-slate-300">Войдите в аккаунт, чтобы смотреть урок.</p>
          </div>
        </div>

        <div
          v-else-if="manifestLoading || isManifestProcessing"
          class="flex h-full items-center justify-center bg-slate-950/95 px-4 sm:px-6"
        >
          <div class="space-y-4 text-center">
            <div class="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400"></div>
            <p class="text-sm font-semibold text-slate-300">Видео обрабатывается для HLS-воспроизведения...</p>
            <p class="text-xs text-slate-500">Страница обновит статус автоматически.</p>
          </div>
        </div>

        <div
          v-else-if="manifestError"
          class="flex h-full items-center justify-center bg-slate-950/95 px-4 text-center text-rose-300 sm:px-6"
        >
          <div>
            <p class="font-semibold">Видео недоступно</p>
            <p class="mt-1 text-sm text-rose-200/80">{{ manifestError }}</p>
          </div>
        </div>

        <iframe
          v-else-if="showLegacyVideo && legacyEmbedUrl"
          class="h-full w-full"
          :src="legacyEmbedUrl"
          title="Видео урока"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen
        ></iframe>

        <video
          v-else-if="showLegacyVideo && !legacyEmbedUrl"
          class="h-full w-full object-contain"
          :src="fallbackVideoUrl"
          controls
          preload="metadata"
        ></video>

        <video
          v-else
          ref="videoElement"
          class="h-full w-full object-contain"
          controls
          preload="metadata"
        ></video>

        <div
          v-if="showLegacyVideo && playbackNotice"
          class="absolute right-3 top-3 rounded-full border border-amber-400/30 bg-slate-950/85 px-3 py-1 text-[11px] font-semibold text-amber-100"
        >
          {{ playbackNotice }}
        </div>
      </section>

      <header class="border-b border-slate-800 bg-slate-900/65 px-4 py-5 sm:px-6">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="mb-3 flex flex-wrap items-center gap-2">
              <span class="inline-flex items-center rounded-full border border-indigo-400/25 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-indigo-200">
                {{ lessonTypeLabel }}
              </span>
              <span
                class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold"
                :class="isCompleted
                  ? 'border-emerald-400/25 bg-emerald-500/10 text-emerald-200'
                  : 'border-slate-700 bg-slate-950/45 text-slate-300'"
              >
                <svg v-if="isCompleted" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <span v-else class="h-2 w-2 rounded-full bg-indigo-300"></span>
                {{ isCompleted ? 'Завершён' : 'В процессе' }}
              </span>
              <span v-if="isPreviewMode" class="inline-flex rounded-full border border-amber-400/25 bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-200">
                Предпросмотр
              </span>
            </div>

            <h1 class="break-words text-xl font-black leading-tight text-slate-100 sm:text-3xl">{{ lesson.title }}</h1>
            <p class="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{{ lessonHint }}</p>
          </div>

          <div class="grid gap-2 sm:flex sm:flex-wrap">
            <select
              v-if="isVideoLesson && availableLevels.length > 0"
              v-model.number="selectedLevel"
              class="w-full rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm font-semibold text-slate-200 outline-none transition focus:border-indigo-400 sm:w-auto"
              @change="applyQuality"
            >
              <option v-for="option in qualityOptions" :key="option.value" :value="option.value">
                Качество: {{ option.label }}
              </option>
            </select>
          </div>
        </div>
      </header>

      <div v-if="isVideoLesson && resumePromptVisible" class="border-b border-emerald-400/15 bg-emerald-500/10 px-5 py-4 sm:px-6">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-sm font-bold text-emerald-100">Продолжить просмотр?</p>
            <p class="text-sm text-emerald-200/80">Сохранённая позиция: {{ savedTimeLabel }}</p>
          </div>
          <div class="grid gap-2 sm:flex sm:flex-wrap">
            <button
              class="rounded-xl border border-emerald-400/30 bg-emerald-500/20 px-4 py-2 text-sm font-bold text-emerald-100 transition hover:bg-emerald-500/30"
              @click="jumpToSavedTime"
            >
              Продолжить
            </button>
            <button
              class="rounded-xl border border-slate-700 bg-slate-950/60 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-slate-500"
              @click="startFromBeginning"
            >
              Сначала
            </button>
          </div>
        </div>
      </div>

      <main class="min-w-0 p-4 sm:p-6">
        <div v-if="isTextLesson || isVideoLesson">
          <div
            v-if="cleanHtmlContent"
            class="prose prose-invert max-w-none break-words rounded-2xl border border-slate-800 bg-slate-950/30 p-4 text-slate-300 prose-headings:text-slate-100 prose-a:text-indigo-300 prose-img:max-w-full prose-pre:overflow-x-auto prose-table:block prose-table:overflow-x-auto sm:p-5"
            v-html="cleanHtmlContent"
          ></div>
          <div v-else class="rounded-2xl border border-dashed border-slate-800 bg-slate-950/30 p-6 text-sm text-slate-500">
            Описание к уроку пока не добавлено.
          </div>
        </div>

        <section v-if="isQuizLesson" class="space-y-5">
          <div v-if="quizLoading" class="rounded-2xl border border-slate-800 bg-slate-950/30 p-6 text-center text-slate-400">
            <div class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-400"></div>
            <p class="mt-3 text-sm font-medium">Загрузка теста...</p>
          </div>

          <div v-else-if="quizData" class="space-y-5">
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Вопросы</p>
                <p class="mt-1 text-2xl font-black text-slate-100">{{ quizQuestions.length }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Ответы</p>
                <p class="mt-1 text-2xl font-black text-indigo-300">{{ answeredQuestionsCount }}/{{ quizQuestions.length }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Попытки</p>
                <p class="mt-1 text-2xl font-black text-slate-100">{{ attemptsUsed }}/{{ maxAttempts || '∞' }}</p>
              </div>
              <div class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
                <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">Проходной балл</p>
                <p class="mt-1 text-2xl font-black text-emerald-300">{{ quizConfig?.passing_score_percentage || 0 }}%</p>
              </div>
            </div>

            <div class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div class="min-w-0">
                  <p class="text-sm font-bold text-slate-200">Готовность к отправке</p>
                  <p class="text-sm text-slate-500">Заполните все вопросы перед проверкой результата.</p>
                </div>
                <div v-if="hasTimeLimit" class="inline-flex w-fit items-center gap-2 rounded-xl border px-3 py-2 text-sm font-black" :class="timerSecondsLeft <= 60 ? 'border-rose-400/30 bg-rose-500/10 text-rose-200' : 'border-indigo-400/30 bg-indigo-500/10 text-indigo-200'">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 8v5l3 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                    <path d="M12 22a9 9 0 100-18 9 9 0 000 18z" stroke="currentColor" stroke-width="1.8" />
                  </svg>
                  {{ timerLabel }}
                </div>
              </div>
              <div class="mt-4 h-2 overflow-hidden rounded-full bg-slate-900">
                <div class="h-full rounded-full bg-indigo-500 transition-all duration-300" :style="{ width: `${quizAnswerProgress}%` }"></div>
              </div>
            </div>

            <div
              v-if="isBlocked"
              class="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-200"
            >
              Тест временно заблокирован до {{ formattedBlockedUntil }}.
            </div>

            <div
              v-if="quizError"
              class="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-300"
            >
              {{ quizError }}
            </div>

            <div class="space-y-4">
              <div
                v-for="(question, index) in quizQuestions"
                :key="question.id"
                class="rounded-2xl border border-slate-800 bg-slate-950/35 p-4 sm:p-5"
              >
                <div class="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0">
                    <p class="text-xs font-bold uppercase tracking-[0.22em] text-indigo-300">Вопрос {{ index + 1 }}</p>
                    <h3 class="mt-2 break-words text-base font-bold leading-relaxed text-slate-100 sm:text-lg">{{ question.text }}</h3>
                  </div>
                  <span class="w-fit shrink-0 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-bold text-slate-400">
                    {{ question.is_multiple ? 'Несколько ответов' : 'Один ответ' }}
                  </span>
                </div>

                <div class="grid gap-2">
                  <label
                    v-for="choice in question.choices"
                    :key="choice.id"
                    class="group flex min-w-0 cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition"
                    :class="isChoiceSelected(question, choice)
                      ? 'border-indigo-400/70 bg-indigo-500/15 text-slate-100'
                      : 'border-slate-800 bg-slate-900/35 text-slate-300 hover:border-slate-600 hover:bg-slate-900/70'"
                  >
                    <input
                      v-if="question.is_multiple"
                      type="checkbox"
                      class="sr-only"
                      :checked="Array.isArray(quizAnswers[question.id]) && quizAnswers[question.id].includes(choice.id)"
                      :disabled="quizInputsDisabled"
                      @change="toggleMultiAnswer(question.id, choice.id)"
                    >
                    <input
                      v-else
                      type="radio"
                      class="sr-only"
                      :name="`q-${question.id}`"
                      :checked="quizAnswers[question.id] === choice.id"
                      :disabled="quizInputsDisabled"
                      @change="setSingleAnswer(question.id, choice.id)"
                    >
                    <span
                      class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border transition"
                      :class="[
                        question.is_multiple ? 'rounded-md' : 'rounded-full',
                        isChoiceSelected(question, choice)
                          ? 'border-indigo-300 bg-indigo-500 text-white'
                          : 'border-slate-600 bg-slate-950 text-transparent group-hover:border-slate-400',
                      ]"
                    >
                      <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
                      </svg>
                    </span>
                    <span class="min-w-0 break-words text-sm font-medium leading-relaxed">{{ choice.text }}</span>
                  </label>
                </div>
              </div>
            </div>

            <div
              v-if="quizResult"
              class="rounded-3xl border p-5"
              :class="quizResult.is_passed
                ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100'
                : 'border-rose-400/30 bg-rose-500/10 text-rose-100'"
            >
              <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm font-bold uppercase tracking-[0.22em]" :class="quizResult.is_passed ? 'text-emerald-200/80' : 'text-rose-200/80'">
                    {{ quizResult.is_passed ? 'Результат принят' : 'Нужно повторить' }}
                  </p>
                  <h3 class="mt-1 text-2xl font-black">{{ quizResult.score_percentage }}%</h3>
                  <p class="mt-1 text-sm opacity-90">Правильных ответов: {{ quizResult.correct_count }} из {{ quizResult.total_count }}.</p>
                </div>
                <div class="rounded-2xl border border-current/20 bg-black/10 px-5 py-3 text-center">
                  <p class="text-xs font-semibold uppercase tracking-wider opacity-70">Статус</p>
                  <p class="mt-1 font-black">{{ quizResult.is_passed ? 'Пройден' : 'Не пройден' }}</p>
                </div>
              </div>

              <div v-if="quizResult.incorrect_feedback?.length" class="mt-5 space-y-2">
                <p class="text-sm font-bold">Разбор ошибок</p>
                <div
                  v-for="item in quizResult.incorrect_feedback"
                  :key="item.question_id"
                  class="rounded-xl border border-current/20 bg-black/10 p-3 text-sm"
                >
                  <p class="font-semibold">Вопрос #{{ item.question_id }}</p>
                  <p class="mt-1 opacity-90">{{ item.explanation || 'Объяснение для этого вопроса пока не добавлено.' }}</p>
                </div>
              </div>
            </div>

            <div class="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/35 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div class="text-sm text-slate-500">
                <span v-if="!allQuestionsAnswered">Осталось ответить: {{ quizQuestions.length - answeredQuestionsCount }}</span>
                <span v-else-if="isPreviewMode">В предпросмотре отправка отключена.</span>
                <span v-else-if="isBlocked">Отправка временно заблокирована.</span>
                <span v-else-if="isTimeExpired">Время теста истекло.</span>
                <span v-else>Все вопросы заполнены. Можно отправлять.</span>
              </div>

              <button
                class="inline-flex w-full items-center justify-center gap-2 rounded-2xl px-6 py-3 text-sm font-black text-white transition disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                :class="canSubmitQuiz ? 'bg-indigo-600 shadow-lg shadow-indigo-600/20 hover:bg-indigo-500' : 'bg-slate-700'"
                :disabled="!canSubmitQuiz || quizSubmitting"
                @click="submitQuiz"
              >
                <svg v-if="!quizSubmitting" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <span v-else class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
                {{ quizSubmitting ? 'Проверяем...' : 'Отправить ответы' }}
              </button>
            </div>
          </div>

          <div v-else class="rounded-2xl border border-dashed border-slate-800 bg-slate-950/30 p-6 text-center text-slate-500">
            Вопросы для теста пока не добавлены.
          </div>
        </section>
      </main>

      <section v-if="attachments.length" class="border-t border-slate-800 bg-slate-900/45 p-4 sm:p-6">
        <div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 class="text-base font-black text-slate-100">Материалы к уроку</h3>
            <p class="text-sm text-slate-500">Файлы для самостоятельной работы</p>
          </div>
          <span class="rounded-full border border-slate-700 bg-slate-950/50 px-3 py-1 text-xs font-bold text-slate-400">
            {{ attachments.length }} файл.
          </span>
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <a
            v-for="attachment in attachments"
            :key="attachment.id"
            :href="attachment.file_url"
            target="_blank"
            rel="noopener noreferrer"
            class="group flex min-w-0 items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-3 text-sm text-slate-200 transition hover:border-indigo-400/60 hover:bg-indigo-500/10"
          >
            <span class="flex min-w-0 items-center gap-3">
              <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-900 text-slate-400 group-hover:text-indigo-200">
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M8 12l4 4 4-4M12 4v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  <path d="M5 20h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
              </span>
              <span class="truncate font-semibold">{{ attachment.name }}</span>
            </span>
            <span class="shrink-0 text-xs text-slate-500">{{ formatFileSize(attachment.file_size) }}</span>
          </a>
        </div>
      </section>

      <div v-if="attachmentsLoading" class="border-t border-slate-800 p-4 text-sm text-slate-400">Загрузка материалов...</div>

      <footer v-if="!isQuizLesson && !isPreviewMode" class="border-t border-slate-800 bg-slate-900/45 p-4 sm:p-6">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-sm font-bold text-slate-200">Завершение урока</p>
            <p class="text-sm text-slate-500">После завершения откроется следующий доступный материал курса.</p>
          </div>
          <button
            class="inline-flex w-full items-center justify-center gap-2 rounded-2xl px-7 py-3 text-sm font-black text-white transition-all disabled:cursor-default sm:w-auto"
            :class="isCompleted
              ? 'bg-emerald-600/80'
              : 'bg-indigo-600 shadow-lg shadow-indigo-600/20 hover:bg-indigo-500'"
            :disabled="isCompleted || actionLoading"
            @click="completeLesson"
          >
            <svg v-if="isCompleted" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-else-if="actionLoading" class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"></span>
            <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            {{ isCompleted ? 'Урок завершён' : actionLoading ? 'Сохраняем...' : 'Завершить урок' }}
          </button>
        </div>

        <div
          v-if="actionMessage"
          class="mt-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-300"
        >
          {{ actionMessage }}
        </div>

        <div
          v-if="actionError"
          class="mt-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-300"
        >
          {{ actionError }}
        </div>
      </footer>

      <div v-if="isPreviewMode" class="border-t border-slate-800 bg-amber-500/10 p-5 text-sm text-amber-200">
        Режим предпросмотра: прогресс, просмотр видео и завершение урока не записываются.
      </div>
    </article>
  </div>
</template>
