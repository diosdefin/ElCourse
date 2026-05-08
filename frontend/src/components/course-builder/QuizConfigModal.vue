<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  value: {
    type: Object,
    default: () => ({
      passing_score_percentage: 80,
      max_attempts: 3,
      penalty_hours: 24,
      time_limit_minutes: 0,
    }),
  },
})

const emit = defineEmits(['close', 'save'])

const form = reactive({
  passing_score_percentage: 80,
  max_attempts: 3,
  penalty_hours: 24,
  hasTimeLimit: false,
  time_limit_minutes: 0,
})

watch(
  () => [props.open, props.value],
  () => {
    if (!props.open) {
      return
    }
    form.passing_score_percentage = props.value?.passing_score_percentage ?? 80
    form.max_attempts = props.value?.max_attempts ?? 3
    form.penalty_hours = props.value?.penalty_hours ?? 24
    form.time_limit_minutes = props.value?.time_limit_minutes ?? 0
    form.hasTimeLimit = (props.value?.time_limit_minutes ?? 0) > 0
  },
  { immediate: true, deep: true }
)

const handleSave = () => {
  emit('save', {
    passing_score_percentage: Number(form.passing_score_percentage),
    max_attempts: Math.min(10, Math.max(1, Number(form.max_attempts))),
    penalty_hours: Math.min(168, Math.max(0, Number(form.penalty_hours))),
    time_limit_minutes: form.hasTimeLimit ? Math.max(1, Number(form.time_limit_minutes)) : 0,
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4">
    <div class="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
      <h3 class="text-xl font-bold text-white">Настройки квиза</h3>

      <div class="mt-6 space-y-5">
        <div>
          <label class="mb-2 block text-sm font-medium text-slate-300">Проходной балл: {{ form.passing_score_percentage }}%</label>
          <input v-model.number="form.passing_score_percentage" type="range" min="0" max="100" class="w-full">
        </div>

        <div>
          <label class="mb-2 block text-sm font-medium text-slate-300">Максимум попыток (1-10)</label>
          <input v-model.number="form.max_attempts" type="number" min="1" max="10" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
        </div>

        <div>
          <label class="mb-2 block text-sm font-medium text-slate-300">Штрафные часы (0-168)</label>
          <input v-model.number="form.penalty_hours" type="number" min="0" max="168" class="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-200">
        </div>

        <div class="rounded-xl border border-slate-700 bg-slate-950/80 p-4">
          <label class="flex items-center gap-3 text-sm font-medium text-slate-300">
            <input v-model="form.hasTimeLimit" type="checkbox">
            Ограничить время прохождения
          </label>

          <div v-if="form.hasTimeLimit" class="mt-3">
            <input v-model.number="form.time_limit_minutes" type="number" min="1" class="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-200" placeholder="Минуты">
          </div>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-2">
        <button class="rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700" @click="emit('close')">Отмена</button>
        <button class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500" @click="handleSave">Сохранить</button>
      </div>
    </div>
  </div>
</template>
