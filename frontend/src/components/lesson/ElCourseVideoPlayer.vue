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
const settingsButtonRef = ref(null)
const settingsMenuRef = ref(null)
const hlsInstance = ref(null)

const currentTime = ref(0)
const duration = ref(0)
const bufferedEnd = ref(0)
const volume = ref(1)
const isMuted = ref(false)
const isPlaying = ref(false)
const isBuffering = ref(false)
const isFullscreen = ref(false)
const isSettingsOpen = ref(false)
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
const showQualitySelector = computed(() => isHlsReady.value && availableLevels.value.length > 0)
const canOpenSettings = computed(() => showCustomControls.value)

const statusMeta = computed(() => {
  if (props.playbackMode === 'fallback_video') {
    return {
      label: 'Резервное видео',
      tone: 'border-amber-400/25 bg-amber-500/10 text-amber-100',
    }
  }
  if (props.playbackMode === 'hls_ready') {
    return {
      label: 'HLS готов',
      tone: 'border-indigo-400/25 bg-indigo-500/10 text-indigo-100',
    }
  }
  if (props.playbackMode === 'hls_processing') {
    return {
      label: 'Видео обрабатывается',
      tone: 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100',
    }
  }
  if (props.playbackMode === 'hls_failed') {
    return {
      label: 'Ошибка обработки',
      tone: 'border-rose-400/25 bg-rose-500/10 text-rose-100',
    }
  }
  return {
    label: 'Видео недоступно',
    tone: 'border-slate-700 bg-slate-900/80 text-slate-200',
  }
})

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

const fullscreenLabel = computed(() => (
  isFullscreen.value ? 'Выйти из полноэкранного режима' : 'Открыть полноэкранный режим'
))

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

  if (hours > 0) {
    return `${hours}:${`${minutes}`.padStart(2, '0')}:${seconds}`
  }
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

function closeSettingsMenu() {
  isSettingsOpen.value = false
}

function toggleSettingsMenu() {
  if (!canOpenSettings.value) return
  isSettingsOpen.value = !isSettingsOpen.value
}

function currentQualityLabel() {
  const option = qualityOptions.value.find((item) => item.value === Number(selectedLevel.value))
  return option?.label || 'Auto'
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

function getFullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || null
}

async function exitFullscreen() {
  const doc = document
  if (typeof doc.exitFullscreen === 'function') {
    await doc.exitFullscreen()
    return
  }
  if (typeof doc.webkitExitFullscreen === 'function') {
    doc.webkitExitFullscreen()
    return
  }
  if (typeof videoRef.value?.webkitExitFullscreen === 'function') {
    videoRef.value.webkitExitFullscreen()
  }
}

async function enterFullscreen() {
  const target = wrapperRef.value
  if (!target) return

  if (typeof target.requestFullscreen === 'function') {
    await target.requestFullscreen()
    return
  }
  if (typeof target.webkitRequestFullscreen === 'function') {
    target.webkitRequestFullscreen()
    return
  }
  if (typeof videoRef.value?.webkitEnterFullscreen === 'function') {
    videoRef.value.webkitEnterFullscreen()
  }
}

async function toggleFullscreen() {
  try {
    if (getFullscreenElement() || videoRef.value?.webkitDisplayingFullscreen) {
      await exitFullscreen()
    } else {
      await enterFullscreen()
    }
  } catch (error) {
  }
}

function applySelectedQuality() {
  if (!hlsInstance.value) return
  hlsInstance.value.currentLevel = Number(selectedLevel.value)
  emit('quality-change', selectedLevel.value)
  showQualityNotice(`Качество: ${currentQualityLabel()}`)
}

function selectQuality(value) {
  selectedLevel.value = Number(value)
  applySelectedQuality()
  closeSettingsMenu()
}

function selectSpeed(value) {
  playbackSpeed.value = Number(value)
  closeSettingsMenu()
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
    ['webkitbeginfullscreen', () => {
      isFullscreen.value = true
    }],
    ['webkitendfullscreen', () => {
      isFullscreen.value = false
    }],
  ]

  listeners.forEach(([eventName, handler]) => video.addEventListener(eventName, handler))
  removeMediaListeners = () => {
    listeners.forEach(([eventName, handler]) => video.removeEventListener(eventName, handler))
  }
}

function teardownPlayer() {
  removeMediaListeners()
  closeSettingsMenu()

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
      emit('quality-change', -1)
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

function handleSettingsPointerDown(event) {
  if (!isSettingsOpen.value) return
  const target = event.target
  if (settingsButtonRef.value?.contains(target) || settingsMenuRef.value?.contains(target)) {
    return
  }
  closeSettingsMenu()
}

function handleKeydown(event) {
  if (event.key === 'Escape' && isSettingsOpen.value) {
    event.preventDefault()
    closeSettingsMenu()
    return
  }

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
  isFullscreen.value = Boolean(getFullscreenElement() || videoRef.value?.webkitDisplayingFullscreen)
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
  document.addEventListener('pointerdown', handleSettingsPointerDown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('pointerdown', handleSettingsPointerDown)
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
  <section
    ref="wrapperRef"
    class="relative overflow-hidden rounded-[1.8rem] border border-slate-700/50 bg-slate-950 shadow-[0_24px_60px_rgba(2,6,23,0.45)]"
  >
    <div class="relative aspect-video bg-black">
      <div
        v-if="playbackMode === 'hls_processing'"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/94 px-4 text-center"
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
        class="absolute inset-0 flex items-center justify-center bg-slate-950/94 px-4 text-center"
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
        @click="togglePlayPause"
      ></video>

      <div
        v-if="showCustomControls"
        class="pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-transparent"
      >
        <div class="absolute inset-0 flex items-center justify-center px-4 sm:px-8">
          <div
            class="pointer-events-auto flex items-center gap-3 rounded-full border border-white/10 bg-slate-950/32 px-3 py-3 shadow-[0_18px_45px_rgba(2,6,23,0.45)] backdrop-blur-2xl transition sm:gap-4"
            :class="isPlaying ? 'opacity-88' : 'opacity-100'"
          >
            <button
              type="button"
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/12 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-12 sm:w-12"
              aria-label="Назад на 10 секунд"
              @click.stop="skipBy(-10)"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M11 7L6 12l5 5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M18 7l-5 5 5 5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>

            <button
              type="button"
              class="inline-flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-slate-950/78 text-white shadow-2xl shadow-black/40 backdrop-blur-xl transition hover:bg-slate-900/90 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-16 sm:w-16"
              aria-label="Воспроизвести или поставить на паузу"
              @click.stop="togglePlayPause"
            >
              <svg v-if="!isPlaying" class="ml-1 h-6 w-6 sm:h-7 sm:w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6.5v11l9-5.5-9-5.5z" />
              </svg>
              <svg v-else class="h-6 w-6 sm:h-7 sm:w-7" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6h3v12H8zm5 0h3v12h-3z" />
              </svg>
            </button>

            <button
              type="button"
              class="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/12 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-12 sm:w-12"
              aria-label="Вперёд на 10 секунд"
              @click.stop="skipBy(10)"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M13 7l5 5-5 5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M6 7l5 5-5 5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <div class="absolute inset-x-0 bottom-0 px-3 pb-3 pt-16 sm:px-5 sm:pb-5">
          <div class="pointer-events-auto rounded-[1.35rem] border border-white/10 bg-slate-950/66 p-3 shadow-[0_18px_40px_rgba(2,6,23,0.42)] backdrop-blur-2xl sm:p-4">
            <div class="relative">
              <div class="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/10"></div>
              <div
                class="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/20"
                :style="{ width: `${bufferedPercent}%` }"
              ></div>
              <div
                class="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-indigo-400"
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

            <div class="mt-3 flex flex-wrap items-center gap-2 sm:gap-3">
              <span class="text-xs font-semibold tabular-nums text-slate-300 sm:text-sm">
                {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
              </span>

              <span
                class="inline-flex min-h-8 items-center rounded-full border px-3 py-1 text-[11px] font-semibold sm:text-xs"
                :class="statusMeta.tone"
              >
                {{ statusMeta.label }}
              </span>

              <div
                v-if="qualityNotice"
                class="inline-flex rounded-full border border-indigo-400/25 bg-indigo-500/10 px-3 py-1 text-[11px] font-semibold text-indigo-100 sm:text-xs"
              >
                {{ qualityNotice }}
              </div>

              <div class="ml-auto flex items-center gap-2">
                <div class="relative">
                  <button
                    ref="settingsButtonRef"
                    type="button"
                    class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                    aria-label="Настройки плеера"
                    aria-haspopup="menu"
                    :aria-expanded="isSettingsOpen"
                    @click.stop="toggleSettingsMenu"
                  >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 6.5a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 7a1.5 1.5 0 110-3 1.5 1.5 0 010 3zm0 7a1.5 1.5 0 110-3 1.5 1.5 0 010 3z" fill="currentColor" />
                    </svg>
                  </button>

                  <div
                    v-if="isSettingsOpen && canOpenSettings"
                    ref="settingsMenuRef"
                    class="absolute bottom-12 right-0 z-20 w-[min(18rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-white/10 bg-slate-950/92 p-3 shadow-[0_18px_45px_rgba(2,6,23,0.52)] backdrop-blur-2xl"
                    role="menu"
                  >
                    <div class="space-y-3">
                      <div class="space-y-2">
                        <div class="flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                          <span>Скорость</span>
                          <span class="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-slate-300">{{ playbackSpeed }}x</span>
                        </div>
                        <div class="flex flex-wrap gap-2">
                          <button
                            v-for="speed in SPEED_OPTIONS"
                            :key="speed"
                            type="button"
                            class="inline-flex min-h-9 items-center justify-center rounded-full border px-3 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                            :class="playbackSpeed === speed
                              ? 'border-indigo-400/35 bg-indigo-500/15 text-indigo-100'
                              : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10'"
                            :aria-label="`Скорость ${speed}x`"
                            @click.stop="selectSpeed(speed)"
                          >
                            {{ speed }}x
                          </button>
                        </div>
                      </div>

                      <div v-if="showQualitySelector" class="space-y-2">
                        <div class="flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                          <span>Качество</span>
                          <span class="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-slate-300">{{ currentQualityLabel() }}</span>
                        </div>
                        <div class="flex flex-wrap gap-2">
                          <button
                            v-for="option in qualityOptions"
                            :key="option.value"
                            type="button"
                            class="inline-flex min-h-9 items-center justify-center rounded-full border px-3 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                            :class="selectedLevel === option.value
                              ? 'border-indigo-400/35 bg-indigo-500/15 text-indigo-100'
                              : 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10'"
                            :aria-label="`Качество ${option.label}`"
                            @click.stop="selectQuality(option.value)"
                          >
                            {{ option.label }}
                          </button>
                        </div>
                      </div>

                      <div class="space-y-2">
                        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Звук</div>
                        <div class="flex items-center gap-3">
                          <button
                            type="button"
                            class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                            :aria-label="isMuted || volume === 0 ? 'Включить звук' : 'Выключить звук'"
                            @click.stop="toggleMute"
                          >
                            <svg v-if="isMuted || volume === 0" class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                              <path d="M15 9l-6 6m0-6l6 6M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                            </svg>
                            <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                              <path d="M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                              <path d="M16 9.5a3.5 3.5 0 010 5M18.5 7a7 7 0 010 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                            </svg>
                          </button>

                          <input
                            :value="isMuted ? 0 : volume"
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            class="player-range w-full"
                            aria-label="Громкость"
                            @input="applyVolume($event.target.value)"
                          >
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                  :aria-label="fullscreenLabel"
                  :title="fullscreenLabel"
                  @click.stop="toggleFullscreen"
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
      </div>

      <div
        v-if="showCustomControls && isBuffering"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
      >
        <div class="rounded-full border border-white/10 bg-slate-950/72 p-4 shadow-xl shadow-black/30 backdrop-blur-xl">
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
  border: 1px solid rgba(255, 255, 255, 0.24);
  background: #f8fafc;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.45);
  transition: transform 0.16s ease;
}

.player-range:hover::-webkit-slider-thumb {
  transform: scale(1.08);
}

.player-range::-moz-range-track {
  height: 4px;
  border-radius: 9999px;
  background: transparent;
}

.player-range::-moz-range-thumb {
  height: 16px;
  width: 16px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 9999px;
  background: #f8fafc;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.45);
  transition: transform 0.16s ease;
}

.player-range:hover::-moz-range-thumb {
  transform: scale(1.08);
}
</style>
