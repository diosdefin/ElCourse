<script setup>
import { resolveMediaUrl } from '@/utils/media'
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
// Наш железный фикс путей
const safeManifestUrl = computed(() => {
  return resolveMediaUrl(props.manifestUrl)
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
const SPEED_OPTIONS = [0.5, 0.75, 1, 1.5, 2]
const CONTROLS_HIDE_DELAY = 3000
const QUICK_CONTROLS_HIDE_DELAY = 900
const VOLUME_HIDE_DELAY = 2000
const CLICK_DELAY = 220

const wrapperRef = ref(null)
const videoRef = ref(null)
const settingsButtonRef = ref(null)
const settingsMenuRef = ref(null)
const volumeButtonRef = ref(null)
const volumePanelRef = ref(null)
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
const settingsView = ref('main')
const isVolumePanelOpen = ref(false)
const isPictureInPicture = ref(false)
const controlsVisible = ref(true)
const playbackSpeed = ref(1)
const availableLevels = ref([])
const selectedLevel = ref(-1)
const qualityNotice = ref('')

let removeMediaListeners = () => {}
let readyEmitted = false
let qualityNoticeTimer = null
let controlsHideTimer = null
let volumeHideTimer = null
let videoClickTimer = null

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
const isControlsVisible = computed(() => !isPlaying.value || controlsVisible.value || isSettingsOpen.value || isVolumePanelOpen.value)
const speedIndex = computed(() => Math.max(0, SPEED_OPTIONS.indexOf(Number(playbackSpeed.value))))

const supportsPictureInPicture = computed(() => (
  showCustomControls.value
  && typeof document !== 'undefined'
  && Boolean(document.pictureInPictureEnabled)
  && !videoRef.value?.disablePictureInPicture
))

const showStatusBadge = computed(() => (
  props.playbackMode === 'fallback_video'
  || props.playbackMode === 'hls_processing'
  || props.playbackMode === 'hls_failed'
  || props.playbackMode === 'no_video'
))

const statusMeta = computed(() => {
  if (props.playbackMode === 'fallback_video') {
    return {
      label: 'Резервное видео',
      tone: 'border-amber-400/25 bg-amber-500/10 text-amber-100',
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
  if (props.playbackMode === 'hls_ready') {
    return {
      label: 'HLS готов',
      tone: 'border-indigo-400/25 bg-indigo-500/10 text-indigo-100',
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

function clearControlsTimer() {
  if (controlsHideTimer) {
    window.clearTimeout(controlsHideTimer)
    controlsHideTimer = null
  }
}

function scheduleControlsHide(delay = CONTROLS_HIDE_DELAY) {
  clearControlsTimer()
  if (!isPlaying.value || isSettingsOpen.value || isVolumePanelOpen.value) return
  controlsHideTimer = window.setTimeout(() => {
    controlsVisible.value = false
    controlsHideTimer = null
  }, delay)
}

function revealControls(delay = CONTROLS_HIDE_DELAY) {
  controlsVisible.value = true
  scheduleControlsHide(delay)
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
  settingsView.value = 'main'
  scheduleControlsHide()
}

function toggleSettingsMenu() {
  if (!canOpenSettings.value) return
  isSettingsOpen.value = !isSettingsOpen.value
  if (isSettingsOpen.value) {
    settingsView.value = 'main'
    revealControls()
  } else {
    scheduleControlsHide()
  }
}

function openSettingsView(view) {
  settingsView.value = view
  revealControls()
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

function setSpeedByIndex(index) {
  const numeric = Number(index)
  const option = SPEED_OPTIONS[numeric]
  if (!option) return
  playbackSpeed.value = option
  revealControls()
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
  revealControls()
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
      revealControls(QUICK_CONTROLS_HIDE_DELAY)
    } catch (error) {
      emitPlayerError('Не удалось запустить воспроизведение.')
    }
    return
  }

  videoRef.value.pause()
  controlsVisible.value = true
}

function toggleMute() {
  if (!videoRef.value) return
  videoRef.value.muted = !videoRef.value.muted
  isMuted.value = videoRef.value.muted
  revealControls()
}

function applyVolume(value) {
  if (!videoRef.value) return
  const numeric = Math.min(Math.max(Number(value) || 0, 0), 1)
  videoRef.value.volume = numeric
  volume.value = numeric
  videoRef.value.muted = numeric === 0
  isMuted.value = videoRef.value.muted
  revealControls()
}

function openVolumePanel() {
  if (!showCustomControls.value) return
  if (volumeHideTimer) {
    window.clearTimeout(volumeHideTimer)
    volumeHideTimer = null
  }
  isVolumePanelOpen.value = true
  revealControls()
}

function scheduleVolumePanelClose() {
  if (volumeHideTimer) {
    window.clearTimeout(volumeHideTimer)
  }
  volumeHideTimer = window.setTimeout(() => {
    isVolumePanelOpen.value = false
    volumeHideTimer = null
    scheduleControlsHide()
  }, VOLUME_HIDE_DELAY)
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
    revealControls()
  } catch (error) {
  }
}

async function togglePictureInPicture() {
  if (!videoRef.value || !supportsPictureInPicture.value) return

  try {
    if (document.pictureInPictureElement) {
      await document.exitPictureInPicture()
    } else {
      await videoRef.value.requestPictureInPicture()
    }
    revealControls()
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
  revealControls()
}

function selectSpeed(value) {
  playbackSpeed.value = normalizePlaybackSpeed(value)
  revealControls()
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
      scheduleControlsHide(QUICK_CONTROLS_HIDE_DELAY)
    }],
    ['playing', () => {
      isPlaying.value = true
      isBuffering.value = false
      scheduleControlsHide(QUICK_CONTROLS_HIDE_DELAY)
    }],
    ['pause', () => {
      isPlaying.value = false
      controlsVisible.value = true
      emit('progress-save', currentTime.value)
    }],
    ['waiting', () => {
      isBuffering.value = true
      revealControls()
    }],
    ['seeking', () => {
      isBuffering.value = true
    }],
    ['seeked', () => {
      isBuffering.value = false
      currentTime.value = Number(video.currentTime || 0)
      emit('seek', currentTime.value)
      emit('progress-save', currentTime.value)
      scheduleControlsHide()
    }],
    ['volumechange', () => {
      volume.value = Number(video.volume || 0)
      isMuted.value = Boolean(video.muted)
    }],
    ['enterpictureinpicture', () => {
      isPictureInPicture.value = true
    }],
    ['leavepictureinpicture', () => {
      isPictureInPicture.value = false
    }],
    ['ended', () => {
      isPlaying.value = false
      controlsVisible.value = true
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
  clearControlsTimer()

  if (volumeHideTimer) {
    window.clearTimeout(volumeHideTimer)
    volumeHideTimer = null
  }
  isVolumePanelOpen.value = false

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
  isPictureInPicture.value = false
  controlsVisible.value = true
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
    hls.loadSource(resolveMediaUrl(props.manifestUrl))
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
    video.src = resolveMediaUrl(props.manifestUrl)
    video.load()
    return
  }

  emitPlayerError('Браузер не поддерживает HLS-воспроизведение.')
}

function handleTimelineInput(event) {
  seekTo(event.target.value)
}

function handleVideoClick() {
  if (videoClickTimer) {
    window.clearTimeout(videoClickTimer)
    videoClickTimer = null
  }

  videoClickTimer = window.setTimeout(() => {
    togglePlayPause()
    videoClickTimer = null
  }, CLICK_DELAY)
}

function handleVideoDoubleClick() {
  if (videoClickTimer) {
    window.clearTimeout(videoClickTimer)
    videoClickTimer = null
  }
  toggleFullscreen()
}

function handlePlayerInteraction() {
  if (!showCustomControls.value) return
  revealControls()
}

function handlePlayerLeave() {
  scheduleControlsHide(QUICK_CONTROLS_HIDE_DELAY)
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
  if (event.key === 'Escape') {
    if (isSettingsOpen.value) {
      event.preventDefault()
      if (settingsView.value !== 'main') {
        settingsView.value = 'main'
      } else {
        closeSettingsMenu()
      }
      return
    }
    if (isVolumePanelOpen.value) {
      event.preventDefault()
      isVolumePanelOpen.value = false
      return
    }
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
  revealControls()
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
  if (controlsHideTimer) {
    window.clearTimeout(controlsHideTimer)
    controlsHideTimer = null
  }
  if (volumeHideTimer) {
    window.clearTimeout(volumeHideTimer)
    volumeHideTimer = null
  }
  if (videoClickTimer) {
    window.clearTimeout(videoClickTimer)
    videoClickTimer = null
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
    class="elcourse-player relative overflow-hidden rounded-[1.65rem] border border-slate-700/45 bg-slate-950 shadow-[0_24px_60px_rgba(2,6,23,0.45)]"
    @pointermove="handlePlayerInteraction"
    @touchstart.passive="handlePlayerInteraction"
    @mouseleave="handlePlayerLeave"
  >
    <div class="video-frame relative aspect-video bg-black">
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
        @click="handleVideoClick"
        @dblclick.prevent="handleVideoDoubleClick"
      ></video>

      <div
        v-if="showCustomControls"
        class="control-layer pointer-events-none absolute inset-0 bg-gradient-to-t from-slate-950/86 via-slate-950/8 to-transparent transition-opacity duration-200"
        :class="isControlsVisible ? 'opacity-100' : 'opacity-0'"
      >
        <div class="absolute inset-0 flex items-center justify-center px-4 sm:px-8">
          <div
            class="pointer-events-auto flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/52 px-2.5 py-2 shadow-[0_18px_45px_rgba(2,6,23,0.45)] backdrop-blur-2xl transition sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/10 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-11 sm:w-11"
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
              class="inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-slate-950/82 text-white shadow-2xl shadow-black/40 backdrop-blur-xl transition hover:bg-slate-900/90 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-14 sm:w-14"
              aria-label="Воспроизвести или поставить на паузу"
              @click.stop="togglePlayPause"
            >
              <svg v-if="!isPlaying" class="ml-1 h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6.5v11l9-5.5-9-5.5z" />
              </svg>
              <svg v-else class="h-6 w-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 6h3v12H8zm5 0h3v12h-3z" />
              </svg>
            </button>

            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/10 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80 sm:h-11 sm:w-11"
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

        <div class="absolute inset-x-0 bottom-0 px-2 pb-2 pt-14 sm:px-3 sm:pb-3">
          <div class="control-bar pointer-events-auto rounded-[1.15rem] border border-white/10 bg-slate-950/68 px-3 py-2 shadow-[0_16px_36px_rgba(2,6,23,0.42)] backdrop-blur-2xl sm:px-4 sm:py-2.5">
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
                class="player-range relative h-4 w-full cursor-pointer appearance-none bg-transparent"
                aria-label="Позиция воспроизведения"
                @input="handleTimelineInput"
              >
            </div>

            <div class="mt-2 flex flex-wrap items-center gap-2 sm:gap-3">
              <span class="text-xs font-semibold tabular-nums text-slate-300 sm:text-sm">
                {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
              </span>

              <div
                class="relative inline-flex items-center"
                @mouseenter="openVolumePanel"
                @mouseleave="scheduleVolumePanelClose"
                @focusin="openVolumePanel"
                @focusout="scheduleVolumePanelClose"
              >
                <button
                  ref="volumeButtonRef"
                  type="button"
                  class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                  :aria-label="isMuted || volume === 0 ? 'Включить звук' : 'Выключить звук'"
                  @click.stop="toggleMute"
                >
                  <svg v-if="isMuted || volume === 0" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M15 9l-6 6m0-6l6 6M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                  <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M5 10h4l5-4v12l-5-4H5v-4z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    <path d="M16 9.5a3.5 3.5 0 010 5M18.5 7a7 7 0 010 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  </svg>
                </button>

                <div
                  v-if="isVolumePanelOpen"
                  ref="volumePanelRef"
                  class="absolute left-full top-1/2 z-20 ml-2 flex h-9 w-32 -translate-y-1/2 items-center rounded-full border border-white/10 bg-slate-950/86 px-3 shadow-[0_12px_28px_rgba(2,6,23,0.45)] backdrop-blur-2xl"
                >
                  <div class="relative w-full">
                    <div class="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/20"></div>
                    <div
                      class="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-sky-500"
                      :style="{ width: `${(isMuted ? 0 : volume) * 100}%` }"
                    ></div>
                    <input
                      :value="isMuted ? 0 : volume"
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      class="player-range volume-range relative h-5 w-full cursor-pointer appearance-none bg-transparent"
                      aria-label="Громкость"
                      @input="applyVolume($event.target.value)"
                    >
                  </div>
                </div>
              </div>

              <span
                v-if="showStatusBadge"
                class="inline-flex min-h-7 items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold sm:text-[11px]"
                :class="statusMeta.tone"
              >
                {{ statusMeta.label }}
              </span>

              <div
                v-if="qualityNotice"
                class="inline-flex rounded-full border border-indigo-400/25 bg-indigo-500/10 px-2.5 py-1 text-[10px] font-semibold text-indigo-100 sm:text-[11px]"
              >
                {{ qualityNotice }}
              </div>

              <div class="ml-auto flex items-center gap-1.5 sm:gap-2">
                <button
                  v-if="supportsPictureInPicture"
                  type="button"
                  class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                  :aria-label="isPictureInPicture ? 'Закрыть маленькое окно' : 'Открыть в маленьком окне'"
                  :title="isPictureInPicture ? 'Закрыть маленькое окно' : 'Открыть в маленьком окне'"
                  @click.stop="togglePictureInPicture"
                >
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <rect x="4" y="6" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.7" />
                    <rect x="11" y="11" width="7" height="5" rx="1" fill="currentColor" />
                  </svg>
                </button>

                <div class="relative">
                  <button
                    ref="settingsButtonRef"
                    type="button"
                    class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                    aria-label="Настройки плеера"
                    aria-haspopup="menu"
                    :aria-expanded="isSettingsOpen"
                    @click.stop="toggleSettingsMenu"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 6.5a1.35 1.35 0 110-2.7 1.35 1.35 0 010 2.7zm0 6.85a1.35 1.35 0 110-2.7 1.35 1.35 0 010 2.7zm0 6.85a1.35 1.35 0 110-2.7 1.35 1.35 0 010 2.7z" fill="currentColor" />
                    </svg>
                  </button>

                  <div
                    v-if="isSettingsOpen && canOpenSettings"
                    ref="settingsMenuRef"
                    class="settings-panel absolute bottom-11 right-0 z-20 w-[min(16rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-white/10 bg-slate-950/94 shadow-[0_18px_45px_rgba(2,6,23,0.56)] backdrop-blur-2xl"
                    role="menu"
                  >
                    <div v-if="settingsView === 'main'" class="p-2">
                      <button
                        type="button"
                        class="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-slate-100 transition hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                        @click.stop="openSettingsView('speed')"
                      >
                        <span>Скорость</span>
                        <span class="inline-flex items-center gap-2 text-slate-400">
                          {{ playbackSpeed }}x
                          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                        </span>
                      </button>

                      <button
                        v-if="showQualitySelector"
                        type="button"
                        class="mt-1 flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-slate-100 transition hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                        @click.stop="openSettingsView('quality')"
                      >
                        <span>Качество</span>
                        <span class="inline-flex items-center gap-2 text-slate-400">
                          {{ currentQualityLabel() }}
                          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                        </span>
                      </button>
                    </div>

                    <div v-else-if="settingsView === 'speed'" class="p-3">
                      <button
                        type="button"
                        class="mb-2 flex w-full items-center gap-2 rounded-xl px-1.5 py-1.5 text-left text-sm font-bold text-slate-100 transition hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                        @click.stop="settingsView = 'main'"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                        Скорость воспроизведения
                      </button>

                      <div class="rounded-2xl border border-white/10 bg-white/5 p-3">
                        <div class="flex items-center justify-between gap-3">
                          <span class="text-2xl font-black text-white">{{ playbackSpeed }}x</span>
                          <span class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Скорость</span>
                        </div>
                        <div class="relative mt-4">
                          <div class="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/20"></div>
                          <div
                            class="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-sky-500"
                            :style="{ width: `${(speedIndex / (SPEED_OPTIONS.length - 1)) * 100}%` }"
                          ></div>
                          <input
                            :value="speedIndex"
                            type="range"
                            min="0"
                            :max="SPEED_OPTIONS.length - 1"
                            step="1"
                            class="player-range relative h-5 w-full cursor-pointer appearance-none bg-transparent"
                            aria-label="Скорость воспроизведения"
                            @input="setSpeedByIndex($event.target.value)"
                          >
                        </div>
                        <div class="mt-3 grid grid-cols-5 gap-1.5">
                          <button
                            v-for="speed in SPEED_OPTIONS"
                            :key="speed"
                            type="button"
                            class="inline-flex min-h-8 items-center justify-center rounded-full px-2 text-xs font-bold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                            :class="playbackSpeed === speed
                              ? 'bg-white text-slate-950'
                              : 'bg-white/10 text-slate-200 hover:bg-white/10'"
                            @click.stop="selectSpeed(speed)"
                          >
                            {{ speed }}x
                          </button>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="settingsView === 'quality'" class="p-3">
                      <button
                        type="button"
                        class="mb-2 flex w-full items-center gap-2 rounded-xl px-1.5 py-1.5 text-left text-sm font-bold text-slate-100 transition hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                        @click.stop="settingsView = 'main'"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path d="M15 6l-6 6 6 6" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                        Качество
                      </button>

                      <div class="space-y-1">
                        <button
                          v-for="option in qualityOptions"
                          :key="option.value"
                          type="button"
                          class="flex min-h-10 w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-bold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                          :class="selectedLevel === option.value
                            ? 'bg-white text-slate-950'
                            : 'text-slate-100 hover:bg-white/10'"
                          @click.stop="selectQuality(option.value)"
                        >
                          <span>{{ option.label }}</span>
                          <svg v-if="selectedLevel === option.value" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M5 12l4 4 10-10" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  class="fullscreen-button inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10 active:scale-[0.96] focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/80"
                  :aria-label="fullscreenLabel"
                  :title="fullscreenLabel"
                  @click.stop="toggleFullscreen"
                >
                  <svg v-if="!isFullscreen" class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M8.5 4H5a1 1 0 00-1 1v3.5M15.5 4H19a1 1 0 011 1v3.5M8.5 20H5a1 1 0 01-1-1v-3.5M20 15.5V19a1 1 0 01-1 1h-3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                  <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M9 4v4a1 1 0 01-1 1H4M15 4v4a1 1 0 001 1h4M9 20v-4a1 1 0 00-1-1H4M20 15h-4a1 1 0 00-1 1v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
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
.elcourse-player:fullscreen,
.elcourse-player:-webkit-full-screen {
  width: 100vw;
  height: 100vh;
  border-radius: 0;
  border: 0;
  background: #000;
}

.elcourse-player:fullscreen .video-frame,
.elcourse-player:-webkit-full-screen .video-frame {
  height: 100vh;
  aspect-ratio: auto;
}

.elcourse-player:fullscreen .control-bar,
.elcourse-player:-webkit-full-screen .control-bar {
  border-radius: 1rem;
  background: rgba(2, 6, 23, 0.7);
}

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

.volume-range::-webkit-slider-thumb {
  background: #0ea5e9;
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

.volume-range::-moz-range-thumb {
  background: #0ea5e9;
}

.player-range:hover::-moz-range-thumb {
  transform: scale(1.08);
}
</style>
