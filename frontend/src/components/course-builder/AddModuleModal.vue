<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  initialTitle: { type: String, default: '' },
  mode: { type: String, default: 'create' },
})

const emit = defineEmits(['close', 'submit'])

const TITLE_LIMIT = 100
const title = ref('')
const error = ref('')

watch(
  () => props.open,
  (value) => {
    if (value) {
      title.value = props.initialTitle || ''
      error.value = ''
    }
  },
  { immediate: true }
)

const handleSubmit = () => {
  const value = title.value.trim()
  error.value = ''

  if (!value) {
    error.value = 'Укажите название модуля.'
    return
  }

  if (value.length > TITLE_LIMIT) {
    error.value = `Название модуля не должно превышать ${TITLE_LIMIT} символов.`
    return
  }

  emit('submit', { title: value })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-3 backdrop-blur-sm sm:p-4">
    <div class="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border border-slate-700 bg-slate-900 p-5 shadow-2xl shadow-slate-950/50 sm:p-6">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300/80">Структура курса</p>
          <h3 class="mt-1 text-xl font-black text-white">
            {{ mode === 'edit' ? 'Редактировать модуль' : 'Добавить модуль' }}
          </h3>
        </div>
        <button type="button" class="w-full rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-700 sm:w-auto" @click="emit('close')">
          Закрыть
        </button>
      </div>

      <div v-if="error" class="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
        {{ error }}
      </div>

      <div class="mt-4 space-y-2">
        <div class="flex items-center justify-between gap-3">
          <label class="text-sm font-semibold text-slate-300">Название модуля</label>
          <span class="text-xs text-slate-500">{{ title.length }}/{{ TITLE_LIMIT }}</span>
        </div>
        <input
          v-model.trim="title"
          type="text"
          :maxlength="TITLE_LIMIT"
          class="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-indigo-400"
          placeholder="Например: Основы Vue"
          @keyup.enter="handleSubmit"
        >
      </div>

      <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          class="rounded-xl bg-slate-800 px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:bg-slate-700"
          @click="emit('close')"
        >
          Отмена
        </button>
        <button
          type="button"
          class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-500"
          @click="handleSubmit"
        >
          Сохранить
        </button>
      </div>
    </div>
  </div>
</template>
