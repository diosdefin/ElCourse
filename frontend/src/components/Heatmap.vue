<script setup>
import { computed } from 'vue'

const props = defineProps({
  activityData: {
    type: Array,
    default: () => [],
  },
  selectedYear: {
    type: Number,
    default: () => new Date().getFullYear(),
  },
  availableYears: {
    type: Array,
    default: () => [],
  },
  title: {
    type: String,
    default: 'График активности',
  },
  description: {
    type: String,
    default: 'Годовой heatmap активности.',
  },
  counterLabel: {
    type: String,
    default: 'Активностей за год',
  },
  error: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:selectedYear'])

const WEEKDAY_LABELS = ['Вс', '', 'Вт', '', 'Чт', '', 'Сб']
const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'short' })

const formatDateToIso = (date) => {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getActivityLevelClass = (count, inYear = true) => {
  if (!inYear) {
    return 'bg-slate-950/20'
  }
  if (count >= 5) {
    return 'bg-emerald-400'
  }
  if (count >= 3) {
    return 'bg-emerald-600'
  }
  if (count >= 1) {
    return 'bg-emerald-900'
  }
  return 'bg-slate-800'
}

const totalActivityCount = computed(() =>
  props.activityData.reduce((sum, item) => {
    if (!item.date?.startsWith(`${props.selectedYear}-`)) {
      return sum
    }
    return sum + (item.count || 0)
  }, 0)
)

const activityMap = computed(() => {
  const mapped = new Map()
  for (const item of props.activityData) {
    mapped.set(item.date, item.count)
  }
  return mapped
})

const heatmap = computed(() => {
  if (!props.selectedYear) {
    return { weeks: [], monthLabels: {} }
  }

  const startOfYear = new Date(props.selectedYear, 0, 1)
  const endOfYear = new Date(props.selectedYear, 11, 31)

  const gridStart = new Date(startOfYear)
  gridStart.setDate(gridStart.getDate() - gridStart.getDay())

  const gridEnd = new Date(endOfYear)
  gridEnd.setDate(gridEnd.getDate() + (6 - gridEnd.getDay()))

  const weeks = []
  const monthLabels = {}
  let cursor = new Date(gridStart)
  let lastMonth = ''
  let weekIndex = 0

  while (cursor <= gridEnd) {
    const week = []

    for (let day = 0; day < 7; day += 1) {
      const currentDate = new Date(cursor)
      const isoDate = formatDateToIso(currentDate)
      const inYear = currentDate.getFullYear() === props.selectedYear
      const count = inYear ? activityMap.value.get(isoDate) || 0 : 0

      week.push({
        date: isoDate,
        count,
        inYear,
        levelClass: getActivityLevelClass(count, inYear),
        title: inYear ? `${isoDate}: ${count} активностей` : '',
      })

      cursor.setDate(cursor.getDate() + 1)
    }

    const labelSource = week.find((item) => item.inYear && item.date.endsWith('-01')) || week.find((item) => item.inYear)
    if (labelSource) {
      const label = monthFormatter.format(new Date(labelSource.date))
      if (label !== lastMonth) {
        monthLabels[weekIndex] = label
        lastMonth = label
      }
    }

    weeks.push(week)
    weekIndex += 1
  }

  return { weeks, monthLabels }
})
</script>

<template>
  <section class="max-w-full rounded-[2rem] border border-slate-700/50 bg-slate-800/50 p-4 shadow-xl backdrop-blur-md sm:p-8">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div class="min-w-0">
        <h2 class="text-2xl font-bold text-slate-100">{{ title }}</h2>
        <p class="mt-2 text-sm text-slate-400">{{ description }}</p>
      </div>

      <div class="self-start rounded-2xl border border-slate-700 bg-slate-900/50 px-4 py-3 text-left xl:text-right">
        <p class="text-xs uppercase tracking-[0.25em] text-slate-500">{{ counterLabel }}</p>
        <p class="mt-2 text-2xl font-black text-white">{{ totalActivityCount }}</p>
      </div>
    </div>

    <div class="mt-6 grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr),92px]">
      <div class="min-w-0 overflow-hidden rounded-3xl border border-slate-700/50 bg-slate-900/50 p-4">
        <div class="max-w-full overflow-x-auto pb-2">
          <div class="inline-flex min-w-max gap-2 sm:gap-3">
            <div class="pt-5 text-[9px] text-slate-500 sm:pt-7 sm:text-[10px]">
              <div
                v-for="(label, index) in WEEKDAY_LABELS"
                :key="index"
                class="flex h-3 items-center sm:h-4"
              >
                {{ label }}
              </div>
            </div>

            <div class="min-w-0">
              <div class="mb-2 flex gap-0.5 text-[9px] uppercase tracking-[0.12em] text-slate-500 sm:gap-1 sm:text-[10px] sm:tracking-[0.2em]">
                <div
                  v-for="(week, index) in heatmap.weeks"
                  :key="`month-${index}`"
                  class="w-3 sm:w-4"
                >
                  {{ heatmap.monthLabels[index] || '' }}
                </div>
              </div>

              <div class="flex gap-0.5 sm:gap-1">
                <div
                  v-for="(week, weekIndex) in heatmap.weeks"
                  :key="`week-${weekIndex}`"
                  class="flex flex-col gap-0.5 sm:gap-1"
                >
                  <div
                    v-for="day in week"
                    :key="day.date"
                    class="h-3 w-3 rounded-[3px] transition-transform sm:h-4 sm:w-4 sm:rounded-[4px] sm:hover:scale-125"
                    :class="day.levelClass"
                    :title="day.title"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
          <p>Меньше</p>
          <div class="flex items-center gap-2">
            <span class="h-3 w-3 rounded-[4px] bg-slate-800"></span>
            <span class="h-3 w-3 rounded-[4px] bg-emerald-900"></span>
            <span class="h-3 w-3 rounded-[4px] bg-emerald-600"></span>
            <span class="h-3 w-3 rounded-[4px] bg-emerald-400"></span>
          </div>
          <p>Больше</p>
        </div>

        <p v-if="error" class="mt-4 text-sm text-amber-400">{{ error }}</p>
      </div>

      <div v-if="availableYears.length" class="min-w-0 rounded-3xl border border-slate-700/50 bg-slate-900/50 p-3">
        <p class="px-2 text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Год</p>
        <div class="mt-3 space-y-2">
          <button
            v-for="year in availableYears"
            :key="year"
            class="w-full rounded-2xl px-3 py-2 text-sm font-bold transition"
            :class="selectedYear === year
              ? 'bg-white text-slate-950'
              : 'bg-slate-950 text-slate-300 hover:bg-slate-800 hover:text-white'"
            @click="emit('update:selectedYear', year)"
          >
            {{ year }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
