<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

import { TOAST_EVENT_NAME } from '../utils/toast'

const toasts = ref([])

const removeToast = (id) => {
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

const pushToast = (event) => {
  const { type = 'info', message = '', duration = 3800 } = event.detail || {}
  if (!message) {
    return
  }

  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  toasts.value = [...toasts.value, { id, type, message }]
  window.setTimeout(() => removeToast(id), duration)
}

onMounted(() => {
  window.addEventListener(TOAST_EVENT_NAME, pushToast)
})

onUnmounted(() => {
  window.removeEventListener(TOAST_EVENT_NAME, pushToast)
})
</script>

<template>
  <div class="pointer-events-none fixed right-4 top-4 z-[999] flex w-full max-w-sm flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto rounded-2xl border px-4 py-3 text-sm shadow-2xl backdrop-blur"
        :class="toast.type === 'success'
          ? 'border-emerald-500/30 bg-emerald-500/15 text-emerald-200'
          : toast.type === 'error'
            ? 'border-rose-500/30 bg-rose-500/15 text-rose-200'
            : 'border-slate-600 bg-slate-900/85 text-slate-200'"
      >
        {{ toast.message }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}
</style>
