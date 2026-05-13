<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

import { TOAST_EVENT_NAME } from '../utils/toast'

const DISMISS_DISTANCE = 80
const DISMISS_VELOCITY = 0.5
const SNAPBACK_MIN_DURATION = 1200
const EXIT_DURATION = 180

const toasts = ref([])

const clearToastTimer = (toast) => {
  if (toast?.timerId) {
    window.clearTimeout(toast.timerId)
    toast.timerId = null
  }
}

const removeToast = (id) => {
  const toast = toasts.value.find((item) => item.id === id)
  if (toast) {
    clearToastTimer(toast)
  }
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

const scheduleToastRemoval = (toast, delay) => {
  clearToastTimer(toast)
  const safeDelay = Math.max(0, Number(delay) || 0)
  toast.expiresAt = Date.now() + safeDelay
  toast.timerId = window.setTimeout(() => removeToast(toast.id), safeDelay)
}

const dismissToast = (toast, direction = 'up') => {
  if (!toast || toast.dismissing) return

  clearToastTimer(toast)
  toast.dragging = false
  toast.dismissing = true
  toast.dismissDirection = direction

  if (direction === 'left') {
    toast.offsetX = -140
    toast.offsetY = 0
  } else if (direction === 'right') {
    toast.offsetX = 140
    toast.offsetY = 0
  } else {
    toast.offsetX = 0
    toast.offsetY = -110
  }

  window.setTimeout(() => removeToast(toast.id), EXIT_DURATION)
}

const resetToastPosition = (toast) => {
  toast.dragging = false
  toast.pointerId = null
  toast.offsetX = 0
  toast.offsetY = 0
  toast.dismissDirection = null
  scheduleToastRemoval(toast, Math.max(toast.remaining || 0, SNAPBACK_MIN_DURATION))
}

const startDrag = (toast, event) => {
  if (toast.dismissing) return
  if (event.pointerType === 'mouse' && event.button !== 0) return

  clearToastTimer(toast)
  toast.dragging = true
  toast.pointerId = event.pointerId
  toast.startX = event.clientX
  toast.startY = event.clientY
  toast.startTime = Date.now()
  toast.remaining = Math.max(0, (toast.expiresAt || 0) - Date.now())
  toast.offsetX = 0
  toast.offsetY = 0
  toast.dismissDirection = null
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

const moveDrag = (toast, event) => {
  if (!toast.dragging || toast.pointerId !== event.pointerId) return

  toast.offsetX = event.clientX - toast.startX
  toast.offsetY = Math.min(event.clientY - toast.startY, 0)
}

const endDrag = (toast, event) => {
  if (!toast.dragging || toast.pointerId !== event.pointerId) return

  event.currentTarget.releasePointerCapture?.(event.pointerId)

  const elapsed = Math.max(Date.now() - toast.startTime, 1)
  const horizontalDistance = Math.abs(toast.offsetX)
  const upwardDistance = Math.abs(Math.min(toast.offsetY, 0))
  const horizontalVelocity = horizontalDistance / elapsed
  const upwardVelocity = upwardDistance / elapsed

  const shouldDismiss =
    horizontalDistance >= DISMISS_DISTANCE ||
    upwardDistance >= DISMISS_DISTANCE ||
    horizontalVelocity >= DISMISS_VELOCITY ||
    upwardVelocity >= DISMISS_VELOCITY

  if (shouldDismiss) {
    const direction =
      horizontalDistance >= upwardDistance
        ? toast.offsetX < 0
          ? 'left'
          : 'right'
        : 'up'

    dismissToast(toast, direction)
    return
  }

  resetToastPosition(toast)
}

const cancelDrag = (toast, event) => {
  if (!toast.dragging) return
  event?.currentTarget?.releasePointerCapture?.(toast.pointerId)
  resetToastPosition(toast)
}

const toastStyle = (toast) => {
  const dragDistance = Math.max(Math.abs(toast.offsetX), Math.abs(toast.offsetY))
  const opacity = toast.dismissing ? 0 : Math.max(0.5, 1 - dragDistance / 180)

  return {
    transform: `translate3d(${toast.offsetX}px, ${toast.offsetY}px, 0)`,
    opacity,
    transition: toast.dragging ? 'none' : 'transform 180ms ease, opacity 180ms ease',
  }
}

const pushToast = (event) => {
  const { type = 'info', message = '', duration = 3800 } = event.detail || {}
  if (!message) {
    return
  }

  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  const toast = {
    id,
    type,
    message,
    timerId: null,
    expiresAt: 0,
    remaining: duration,
    offsetX: 0,
    offsetY: 0,
    dragging: false,
    pointerId: null,
    startX: 0,
    startY: 0,
    startTime: 0,
    dismissing: false,
    dismissDirection: null,
  }

  toasts.value = [...toasts.value, toast]
  scheduleToastRemoval(toast, duration)
}

onMounted(() => {
  window.addEventListener(TOAST_EVENT_NAME, pushToast)
})

onUnmounted(() => {
  window.removeEventListener(TOAST_EVENT_NAME, pushToast)
  toasts.value.forEach((toast) => clearToastTimer(toast))
})
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 top-0 z-[95] flex justify-end px-3 pt-3 sm:px-4 sm:pt-4">
    <div class="flex w-[calc(100vw-24px)] max-w-sm flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto touch-none select-none overflow-hidden rounded-2xl border border-white/12 bg-[rgba(15,23,42,0.88)] text-slate-100 shadow-[0_20px_48px_rgba(2,6,23,0.46),inset_0_1px_0_rgba(255,255,255,0.12),inset_0_-12px_24px_rgba(15,23,42,0.2)] backdrop-blur-[24px] [backdrop-filter:saturate(170%)_blur(24px)]"
          :class="toast.type === 'success'
            ? 'ring-1 ring-emerald-400/20'
            : toast.type === 'error'
              ? 'ring-1 ring-rose-400/20'
              : 'ring-1 ring-slate-400/10'"
          :style="toastStyle(toast)"
          @pointerdown="startDrag(toast, $event)"
          @pointermove="moveDrag(toast, $event)"
          @pointerup="endDrag(toast, $event)"
          @pointercancel="cancelDrag(toast, $event)"
        >
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent"></div>

          <div class="flex items-start gap-3 px-4 py-3">
            <span
              class="mt-1 inline-flex h-2.5 w-2.5 shrink-0 rounded-full"
              :class="toast.type === 'success'
                ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.4)]'
                : toast.type === 'error'
                  ? 'bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.38)]'
                  : 'bg-sky-300 shadow-[0_0_10px_rgba(125,211,252,0.35)]'"
            ></span>

            <p class="min-w-0 flex-1 break-words pr-1 text-sm font-medium leading-5 text-slate-100">
              {{ toast.message }}
            </p>

            <button
              type="button"
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-slate-300 transition hover:border-white/20 hover:bg-white/[0.08] hover:text-white"
              aria-label="Закрыть уведомление"
              @pointerdown.stop
              @click.stop="dismissToast(toast)"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition-duration: 1ms;
  }

  .toast-enter-from,
  .toast-leave-to {
    opacity: 1;
    transform: none;
  }
}
</style>
