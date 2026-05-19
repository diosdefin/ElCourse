<script setup>
import Hls from 'hls.js'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  manifestUrl: { type: String, default: '' },
  fallbackUrl: { type: String, default: '' },
  playbackMode: { type: String, default: 'no_video' },
  hlsStatus: { type: String, default: '' },
  errorMessage: { type: String, default: '' },
  initialTime: { type: Number, default: 0 },
  preview: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits([
  'ready',
  'timeupdate',
  'progress-save',
  'error',
  'quality-change',
  'speed-change',
  'seek',
  'ended',
])

const SPEED_STORAGE_KEY = 'elcourse_video_speed'
const SPEED_OPTIONS = [0.75, 1, 1.25, 1.5, 2]

const wrapperRef = ref(null)
const videoRef = ref(null)
const hlsInstance = ref(null)

const currentTime = ref(0)
const duration = ref(0)
const bufferedEnd = ref(0)
const volume = ref(1)
const isMuted = ref(false)
const isPlaying = ref(false)
const isBuffering = ref(false)
const isFullscreen = ref(false)
const playbackSpeed = ref(1)
const availableLevels = ref([])
const selectedLevel = ref(-1)
const qualityNotice = ref('')

let removeMediaListeners = () => {}
let readyEmitted = false
let qualityNoticeTimer = null

const isHlsReady = computed(() => props.playbackMode === 'hls_ready' && Boolean(props.manifestUrl))
const isFallbackVideo = computed(() => props.playbackMode === 'fallback_video' && Boolean(props.fallbackUrl))

const youtubeEmbedUrl = computed(() => {
  const url = props.fallbackUrl
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

const isYoutubeFallback = computed(() => isFallbackVideo.value && Boolean(youtubeEmbedUrl.value))
const usesVideoElement = computed(() => (isHlsReady.value || isFallbackVideo.value) && !isYoutubeFallback.value)
const showCustomControls = computed(() => usesVideoElement.value)

const statusMeta = computed(() => {
  if (props.playbackMode === 'fallback_video') {
    return {
      label: 'Fallback',
      tone: 'border-amber-400/30 bg-amber-500/10 text-amber-100',
    }
  }
  if (props.playbackMode === 'hls_ready') {
    return {
      label: 'HLS',
      tone: 'border-indigo-400/30 bg-indigo-500/10 text-indigo-100',
    }
  }
  if (props.playbackMode === 'hls_processing') {
    return {
      label: 'Processing',
      tone: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100',
    }
  }
  if (props.playbackMode === 'hls_failed') {
    return {
      label: 'Failed',
      tone: 'border-rose-400/30 bg-rose-500/10 text-rose-100',
    }
  }
  return {
    label: 'No video',
    tone: 'border-slate-700 bg-slate-900/80 text-slate-200',
  }
})

const timelineMax = computed(() => Math.max(duration.value, 0))
const progressPercent = computed(() => {
  if (!timelineMax.value) return 0
  return Math.min(100, Math.max(0, (currentTime.value / timelineMax.value) * 100))
})
const bufferedPercent = computed(() => {
  if (!timelineMax.value) return 0
  return Math.min(100, Math.max(0, (bufferedEnd.value / timelineMax.value) * 100))
})

const qualityOptions = computed(() => {
  const options = [{ value: -1, label: 'Auto' }]
  for (const level of availableLevels.value) {
    options.push({ value: level.index, label: level.label })
  }
  return options
})

const showQualitySelector = computed(() => isHlsReady.value && availableLevels.value.length > 0)
const fullscreenLabel = computed(() => (
  isFullscreen.value ? 'Выйти из полноэкранного режима' : 'Открыть полноэкранный режим'
))

const overlayTitle = computed(() => {
  if (props.playbackMode === 'hls_processing') return 'Видео обрабатывается'
  if (props.playbackMode === 'hls_failed') return 'Видео недоступно'
  return 'Видео недоступно'
})

const overlayMessage = computed(() => {
  if (props.playbackMode === 'hls_processing') {
    return 'Подготавливаем поток для воспроизведения. Статус обновится автоматически.'
  }
  return props.errorMessage || 'Для этого урока пока нет доступного видеопотока.'
})

function normalizePlaybackSpeed(value) {
  const numeric = Number(value)
  return SPEED_OPTIONS.includes(numeric) ? numeric : 1
}

function readSavedPlaybackSpeed() {
  try {
    return normalizePlaybackSpeed(window.localStorage.getItem(SPEED_STORAGE_KEY))
  } catch (error) {
    return 1
  }
}

function persistPlaybackSpeed() {
  try {
    window.localStorage.setItem(SPEED_STORAGE_KEY, String(playbackSpeed.value))
  } catch (error) {
  }
}

function formatTime(totalSeconds) {
  const normalized = Number(totalSeconds)
  const total = Number.isFinite(normalized) ? Math.max(0, Math.floor(normalized)) : 0
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = `${total % 60}`.padStart(2, '0')
  if (hours > 0) return `${hours}:${`${minutes}`.padStart(2, '0')}:${seconds}`
  return `${minutes}:${seconds}`
}

function showQualityNotice(message) {
  qualityNotice.value = message
  if (qualityNoticeTimer) {
    window.clearTimeout(qualityNoticeTimer)
  }
  qualityNoticeTimer = window.setTimeout(() => {
    qualityNotice.value = ''
    qualityNoticeTimer = null
  }, 1800)
}

function applyPlaybackSpeed() {
  if (videoRef.value) {
    videoRef.value.playbackRate = playbackSpeed.value
  }
}

function syncBufferedRange() {
  const video = videoRef.value
  if (!video || !video.buffered?.length) {
    bufferedEnd.value = 0
    return
  }

  try {
    bufferedEnd.value = video.buffered.end(video.buffered.length - 1)
  } catch (error) {
    bufferedEnd.value = 0
  }
}

function emitReadyIfNeeded() {
  if (readyEmitted || !usesVideoElement.value || !videoRef.value) return
  readyEmitted = true
  emit('ready', {
    duration: duration.value,
    source: isHlsReady.value ? 'hls' : 'fallback_video',
  })
}

function emitPlayerError(message) {
  emit('error', { message })
}

function seekTo(seconds) {
  if (!videoRef.value) return

  const max = Number.isFinite(videoRef.value.duration) && videoRef.value.duration > 0
    ? videoRef.value.duration
    : Math.max(duration.value, 0)
  const nextTime = Math.min(Math.max(Number(seconds) || 0, 0), max || Math.max(Number(seconds) || 0, 0))
  videoRef.value.currentTime = nextTime
  currentTime.value = nextTime
  emit('seek', nextTime)
  emit('progress-save', nextTime)
}

function skipBy(deltaSeconds) {
  if (!videoRef.value) return
  seekTo((videoRef.value.currentTime || 0) + deltaSeconds)
}

async function togglePlayPause() {
  if (!videoRef.value) return

  if (videoRef.value.paused) {
    try {
      await videoRef.value.play()
    } catch (error) {
      emitPlayerError('Не удалось запустить воспроизведение.')
    }
    return
  }

  videoRef.value.pause()
}

function toggleMute() {
  if (!videoRef.value) return
  videoRef.value.muted = !videoRef.value.muted
  isMuted.value = videoRef.value.muted
}

function applyVolume(value) {
  if (!videoRef.value) return
  const numeric = Math.min(Math.max(Number(value) || 0, 0), 1)
  videoRef.value.volume = numeric
  volume.value = numeric
  videoRef.value.muted = numeric === 0
  isMuted.value = videoRef.value.muted
}

async function toggleFullscreen() {
  const target = wrapperRef.value
  if (!target) return

  try {
    const activeElement = document.fullscreenElement || document.webkitFullscreenElement
    if (activeElement) {
      if (typeof document.exitFullscreen === 'function') {
        await document.exitFullscreen()
      } else if (typeof document.webkitExitFullscreen === 'function') {
        document.webkitExitFullscreen()
      }
    } else if (typeof target.requestFullscreen === 'function') {
      await target.requestFullscreen()
    } else if (typeof target.webkitRequestFullscreen === 'function') {
      target.webkitRequestFullscreen()
    }
  } catch (error) {
  }
}

function applySelectedQuality() {
  if (hlsInstance.value) {
    hlsInstance.value.currentLevel = Number(selectedLevel.value)
    emit('quality-change', selectedLevel.value)
    const option = qualityOptions.value.find((item) => item.value === Number(selectedLevel.value))
    showQualityNotice(`Качество: ${option?.label || 'Auto'}`)
  }
}

function attachMediaListeners(video) {
  removeMediaListeners()

  const listeners = [
    ['loadedmetadata', () => {
      duration.value = Number(video.duration || 0)
      applyPlaybackSpeed()
      syncBufferedRange()
      emitReadyIfNeeded()
      if (props.initialTime > 0 && currentTime.value === 0) {
        seekTo(props.initialTime)
      }
    }],
    ['durationchange', () => {
      duration.value = Number(video.duration || 0)
    }],
    ['timeupdate', () => {
      currentTime.value = Number(video.currentTime || 0)
      emit('timeupdate', currentTime.value)
    }],
    ['progress', syncBufferedRange],
    ['play', () => {
      isPlaying.value = true
      isBuffering.value = false
    }],
    ['playing', () => {
      isPlaying.value = true
      isBuffering.value = false
    }],
    ['pause', () => {
      isPlaying.value = false
      emit('progress-save', currentTime.value)
    }],
    ['waiting', () => {
      isBuffering.value = true
    }],
    ['seeking', () => {
      isBuffering.value = true
    }],
    ['seeked', () => {
      isBuffering.value = false
      currentTime.value = Number(video.currentTime || 0)
      emit('seek', currentTime.value)
      emit('progress-save', currentTime.value)
    }],
    ['volumechange', () => {
      volume.value = Number(video.volume || 0)
      isMuted.value = Boolean(video.muted)
    }],
    ['ended', () => {
      isPlaying.value = false
      emit('ended')
      emit('progress-save', currentTime.value)
    }],
    ['error', () => {
      emitPlayerError('Не удалось воспроизвести видео.')
    }],
  ]

  listeners.forEach(([eventName, handler]) => video.addEventListener(eventName, handler))
  removeMediaListeners = () => {
    listeners.forEach(([eventName, handler]) => video.removeEventListener(eventName, handler))
  }
}

function teardownPlayer() {
  removeMediaListeners()
  if (hlsInstance.value) {
    hlsInstance.value.destroy()
    hlsInstance.value = null
  }
  if (videoRef.value) {
    videoRef.value.pause()
    videoRef.value.removeAttribute('src')
    videoRef.value.load()
  }
  availableLevels.value = []
  selectedLevel.value = -1
  currentTime.value = 0
  duration.value = 0
  bufferedEnd.value = 0
  isPlaying.value = false
  isBuffering.value = false
  readyEmitted = false
}

async function setupPlayerSource() {
  teardownPlayer()

  if (!usesVideoElement.value) {
    return
  }

  await nextTick()
  const video = videoRef.value
  if (!video) return

  attachMediaListeners(video)
  video.playsInline = true
  video.preload = 'metadata'
  volume.value = Number(video.volume || 1)
  isMuted.value = Boolean(video.muted)
  applyPlaybackSpeed()

  if (isFallbackVideo.value) {
    video.src = props.fallbackUrl
    video.load()
    return
  }

  if (Hls.isSupported()) {
    const hls = new Hls({
      enableWorker: true,
      capLevelToPlayerSize: true,
      lowLatencyMode: false,
    })
    hlsInstance.value = hls
    hls.attachMedia(video)

    hls.on(Hls.Events.MEDIA_ATTACHED, () => {
      hls.loadSource(props.manifestUrl)
    })

    hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
      availableLevels.value = data.levels.map((level, index) => ({
        index,
        label: level.height ? `${level.height}p` : `Поток ${index + 1}`,
      }))
      selectedLevel.value = -1
      applyPlaybackSpeed()
    })

    hls.on(Hls.Events.ERROR, (_, data) => {
      if (data.fatal) {
        emitPlayerError('Не удалось воспроизвести HLS-поток.')
      }
    })
    return
  }

  if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = props.manifestUrl
    video.load()
    return
  }

  emitPlayerError('Браузер не поддерживает HLS-воспроизведение.')
}

function handleTimelineInput(event) {
  seekTo(event.target.value)
}

function isEditableShortcutTarget(target) {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  const tagName = target.tagName
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT'
}

function handleKeydown(event) {
  if (!showCustomControls.value) return
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return
  if (isEditableShortcutTarget(event.target)) return

  const key = String(event.key || '').toLowerCase()
  if (!key) return

  if (key === ' ' || key === 'k') {
    event.preventDefault()
    togglePlayPause()
    return
  }
  if (key === 'arrowleft' || key === 'j') {
    event.preventDefault()
    skipBy(-10)
    return
  }
  if (key === 'arrowright' || key === 'l') {
    event.preventDefault()
    skipBy(10)
    return
  }
  if (key === 'm') {
    event.preventDefault()
    toggleMute()
    return
  }
  if (key === 'f') {
    event.preventDefault()
    toggleFullscreen()
  }
}

function handleFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement || document.webkitFullscreenElement)
}

watch(
  () => [props.manifestUrl, props.fallbackUrl, props.playbackMode],
  () => {
    setupPlayerSource()
  },
  { immediate: true }
)

watch(playbackSpeed, (value) => {
  const normalized = normalizePlaybackSpeed(value)
  if (normalized !== value) {
    playbackSpeed.value = normalized
    return
  }
  persistPlaybackSpeed()
  applyPlaybackSpeed()
  emit('speed-change', normalized)
})

onMounted(() => {
  playbackSpeed.value = readSavedPlaybackSpeed()
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
  if (qualityNoticeTimer) {
    window.clearTimeout(qualityNoticeTimer)
    qualityNoticeTimer = null
  }
  teardownPlayer()
})

function getCurrentTime() {
  return videoRef.value ? Number(videoRef.value.currentTime || 0) : 0
}

function hasControllableMedia() {
  return Boolean(showCustomControls.value && videoRef.value)
}

defineExpose({
  getCurrentTime,
  seekTo,
  hasControllableMedia,
  play: togglePlayPause,
  pause: () => videoRef.value?.pause(),
})
</script>

<template>
  <section class="relative overflow-hidden rounded-[1.75rem] border border-slate-700/60 bg-slate-950 shadow-2xl shadow-slate-950/35">
    <div class="relative aspect-video bg-black">
      <div
        v-if="playbackMode === 'hls_processing'"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/95 px-4 text-center"
      >
        <div class="space-y-4">
          <div class="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400"></div>
          <div>
            <p class="font-semibold text-slate-100">{{ overlayTitle }}</p>
            <p class="mt-2 text-sm text-slate-400">{{ overlayMessage }}</p>
          </div>
        </div>
      </div>

      <div
        v-else-if="playbackMode === 'hls_failed' || playbackMode === 'no_video'"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/95 px-4 text-center"
      >
        <div class="space-y-3">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-400/20 bg-rose-500/10 text-rose-200">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 9v4m0 4h.01M10.3 3.9l-8 14A1 1 0 003.2 19h17.6a1 1 0 00.87-1.5l-8-14a1 1 0 00-1.74 0z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-slate-100">{{ overlayTitle }}</p>
            <p class="mt-2 text-sm text-slate-400">{{ overlayMessage }}</p>
          </div>
        </div>
      </div>

      <iframe
        v-else-if="isYoutubeFallback"
        class="h-full w-full"
        :src="youtubeEmbedUrl"
        title="Видео урока"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
      ></iframe>

      <video
        v-else
        ref="videoRef"
        class="h-full w-full object-contain"
        preload="metadata"
      ></video>

      <div
        v-if="showCustomControls && !isPlaying && !isBuffering"
        class="pointer-events-none absolute inset-0 grid place-items-center"
      >
        <button
          type="button"
          class="pointer-events-auto inline-flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-slate-950/70 text-white shadow-2xl shadow-black/40 backdrop-blur-xl transition hover:bg-slate-900/85 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
          aria-label="Воспроизвести или поставить на паузу"
          @click="togglePlayPause"
        >
          <svg v-if="!isPlaying" class="ml-1 h-7 w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8 6.5v11l9-5.5-9-5.5z" />
          </svg>
          <svg v-else class="h-7 w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8 6h3v12H8zm5 0h3v12h-3z" />
          </svg>
        </button>
      </div>

      <div
        v-if="showCustomControls"
        class="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950 via-slate-950/70 to-transparent px-3 pb-3 pt-16 sm:px-5 sm:pb-5"
      >
        <div class="pointer-events-auto rounded-2xl border border-white/10 bg-slate-950/70 p-3 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-4">
          <div class="mb-3 flex items-center justify-between gap-3 text-xs font-semibold text-slate-300">
            <span>{{ formatTime(currentTime) }}</span>
            <span
              class="inline-flex min-h-8 items-center rounded-full border px-3 py-1"
              :class="statusMeta.tone"
            >
              {{ statusMeta.label }}
            </span>
            <span>{{ formatTime(duration) }}</span>
          </div>

          <div class="relative mb-4">
            <div class="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/10"></div>
            <div
              class="absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/20"
              :style="{ width: `${bufferedPercent}%` }"
            ></div>
            <div
              class="absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full bg-indigo-400"
              :style="{ width: `${progressPercent}%` }"
            ></div>
            <input
              :value="currentTime"
              :max="timelineMax || 0"
              min="0"
              step="0.1"
              type="range"
              class="player-range relative h-5 w-full cursor-pointer appearance-none bg-transparent"
              aria-label="Позиция воспроизведения"
              @input="handleTimelineInput"
            >
          </div>

          <div
            v-if="qualityNotice"
            class="mb-3 inline-flex rounded-full border border-indigo-400/25 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-100"
          >
            {{ qualityNotice }}
          </div>

          <div class="flex flex-wrap items-center gap-2 sm:gap-3">
            <button
              type="button"
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
              aria-label="Воспроизвести или поставить на паузу"
              @click="togglePlayPause"
            >
              <svg v-if="!isPlaying" class="ml-0.5 h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6.5v11l9-5.5-9-5.5z" />
              </svg>
              <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6h3v12H8zm5 0h3v12h-3z" />
              </svg>
            </button>

            <button
              type="button"
              class="inline-flex h-10 min-w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 px-3 text-sm font-semibold text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
              aria-label="Назад на 10 секунд"
              @click="skipBy(-10)"
            >
              -10
            </button>

            <button
              type="button"
              class="inline-flex h-10 min-w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 px-3 text-sm font-semibold text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
              aria-label="Вперёд на 10 секунд"
              @click="skipBy(10)"
            >
              +10
            </button>

            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
              aria-label="Включить или выключить звук"
              @click="toggleMute"
            >
              <svg v-if="isMuted || volume === 0" class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M15 9l-6 6m0-6l6 6M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M16 9.5a3.5 3.5 0 010 5M18.5 7a7 7 0 010 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </button>

            <label class="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 sm:inline-flex">
              <span class="text-xs uppercase tracking-wide text-slate-400">Vol</span>
              <input
                :value="isMuted ? 0 : volume"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="player-range w-24"
                aria-label="Громкость"
                @input="applyVolume($event.target.value)"
              >
            </label>

            <div class="ml-auto flex flex-wrap items-center gap-2">
              <label class="inline-flex min-h-10 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 focus-within:ring-2 focus-within:ring-indigo-400/80">
                <span class="text-xs uppercase tracking-wide text-slate-400">Speed</span>
                <select
                  v-model.number="playbackSpeed"
                  class="rounded-full bg-slate-950 px-2 py-1 text-sm font-semibold text-slate-100 outline-none [color-scheme:dark]"
                  style="color-scheme: dark;"
                  aria-label="Скорость воспроизведения"
                >
                  <option v-for="speed in SPEED_OPTIONS" :key="speed" :value="speed" class="bg-slate-950 text-slate-100">
                    {{ speed }}x
                  </option>
                </select>
              </label>

              <label
                v-if="showQualitySelector"
                class="inline-flex min-h-10 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 focus-within:ring-2 focus-within:ring-indigo-400/80"
              >
                <span class="text-xs uppercase tracking-wide text-slate-400">Quality</span>
                <select
                  v-model.number="selectedLevel"
                  class="rounded-full bg-slate-950 px-2 py-1 text-sm font-semibold text-slate-100 outline-none [color-scheme:dark]"
                  style="color-scheme: dark;"
                  aria-label="Качество видео"
                  @change="applySelectedQuality"
                >
                  <option v-for="option in qualityOptions" :key="option.value" :value="option.value" class="bg-slate-950 text-slate-100">
                    {{ option.label }}
                  </option>
                </select>
              </label>

              <button
                type="button"
                class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                aria-label="Полноэкранный режим"
                :aria-label="fullscreenLabel"
                :title="fullscreenLabel"
                @click="toggleFullscreen"
              >
                <svg v-if="!isFullscreen" class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M8 3H4v4M16 3h4v4M8 21H4v-4M20 17v4h-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M9 9H4V4M15 9h5V4M9 15H4v5M20 15v5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="showCustomControls && isBuffering"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
      >
        <div class="rounded-full border border-white/10 bg-slate-950/70 p-4 shadow-xl shadow-black/30 backdrop-blur-xl">
          <div class="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-indigo-400"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.player-range::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 9999px;
  background: transparent;
}

.player-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  margin-top: -6px;
  height: 16px;
  width: 16px;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: #e2e8f0;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.45);
}

.player-range::-moz-range-track {
  height: 4px;
  border-radius: 9999px;
  background: transparent;
}

.player-range::-moz-range-thumb {
  height: 16px;
  width: 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 9999px;
  background: #e2e8f0;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.45);
}
</style>
