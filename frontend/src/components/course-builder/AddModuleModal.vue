<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  initialTitle: { type: String, default: '' },
  mode: { type: String, default: 'create' },
})

const emit = defineEmits(['close', 'submit'])

const title = ref('')

watch(
  () => props.open,
  (value) => {
    if (value) {
      title.value = props.initialTitle || ''
    }
  },
  { immediate: true }
)

const handleSubmit = () => {
  if (!title.value.trim()) {
    return
  }
  emit('submit', { title: title.value.trim() })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4">
    <div class="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
      <h3 class="text-xl font-bold text-white">
        {{ mode === 'edit' ? 'Редактировать модуль' : 'Добавить модуль' }}
      </h3>

      <div class="mt-4 space-y-2">
        <label class="text-sm font-medium text-slate-300">Название</label>
        <input
          v-model="title"
          type="text"
          class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200 outline-none focus:border-indigo-400"
          placeholder="Например: Основы Vue"
        >
      </div>

      <div class="mt-6 flex justify-end gap-2">
        <button
          class="rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700"
          @click="emit('close')"
        >
          Отмена
        </button>
        <button
          class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          @click="handleSubmit"
        >
          Сохранить
        </button>
      </div>
    </div>
  </div>
</template>
