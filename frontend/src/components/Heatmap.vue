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
  if (!inYear) return 'bg-slate-950/20'
  if (count >= 5) return 'bg-emerald-400'
  if (count >= 3) return 'bg-emerald-600'
  if (count >= 1) return 'bg-emerald-900'
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

const shortMonthLabel = (label) => {
  if (!label) return ''
  return label.replace('.', '').slice(0, 1).toUpperCase()
}

const onYearChange = (event) => {
  emit('update:selectedYear', Number(event.target.value))
}
</script>

<template>
  <section class="max-w-full rounded-[1.4rem] border border-slate-700/50 bg-slate-800/50 p-3 shadow-xl backdrop-blur-md sm:p-5 lg:p-6">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div class="min-w-0 max-w-3xl">
        <div class="flex flex-wrap items-center gap-2.5">
          <h2 class="text-base font-bold text-slate-100 sm:text-lg lg:text-xl">{{ title }}</h2>
          <span class="inline-flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900/70 px-2.5 py-1 text-[11px] font-semibold text-slate-300 sm:text-xs">
            <span class="text-slate-500">{{ counterLabel }}</span>
            <span class="text-white">{{ totalActivityCount }}</span>
          </span>
        </div>
        <p class="mt-1.5 max-w-2xl text-xs leading-5 text-slate-400 sm:text-sm sm:leading-6">{{ description }}</p>
      </div>

      <label
        v-if="availableYears.length"
        class="flex shrink-0 items-center gap-2 self-start rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-400"
      >
        <span>Год</span>
        <select
          class="min-w-[78px] bg-transparent text-sm font-semibold text-slate-100 outline-none"
          :value="selectedYear"
          @change="onYearChange"
        >
          <option
            v-for="year in availableYears"
            :key="year"
            :value="year"
            class="bg-slate-900 text-slate-100"
          >
            {{ year }}
          </option>
        </select>
      </label>
    </div>

    <div class="mt-3 min-w-0 overflow-hidden rounded-[1.2rem] border border-slate-700/50 bg-slate-900/55 p-3 sm:mt-4 sm:p-4">
      <div class="max-w-full overflow-x-auto pb-2">
        <div class="inline-flex min-w-max gap-1 sm:gap-2">
          <div class="pt-3 text-[8px] text-slate-500 sm:pt-5 sm:text-[10px]">
            <div
              v-for="(label, index) in WEEKDAY_LABELS"
              :key="index"
              class="flex h-2 items-center sm:h-3.5"
            >
              {{ label }}
            </div>
          </div>

          <div class="min-w-0">
            <div class="mb-1 flex gap-0.5 text-[8px] text-slate-500 sm:mb-1.5 sm:gap-1 sm:text-[10px]">
              <div
                v-for="(week, index) in heatmap.weeks"
                :key="`month-${index}`"
                class="w-2 overflow-hidden sm:w-3.5"
              >
                <span class="sm:hidden">{{ shortMonthLabel(heatmap.monthLabels[index] || '') }}</span>
                <span class="hidden sm:inline">{{ heatmap.monthLabels[index] || '' }}</span>
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
                  class="h-2 w-2 rounded-[2px] transition-transform sm:h-3.5 sm:w-3.5 sm:rounded-[4px] sm:hover:scale-125"
                  :class="day.levelClass"
                  :title="day.title"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 sm:text-xs">
        <p>Меньше</p>
        <div class="flex items-center gap-1.5 sm:gap-2">
          <span class="h-2.5 w-2.5 rounded-[3px] bg-slate-800 sm:h-3 sm:w-3"></span>
          <span class="h-2.5 w-2.5 rounded-[3px] bg-emerald-900 sm:h-3 sm:w-3"></span>
          <span class="h-2.5 w-2.5 rounded-[3px] bg-emerald-600 sm:h-3 sm:w-3"></span>
          <span class="h-2.5 w-2.5 rounded-[3px] bg-emerald-400 sm:h-3 sm:w-3"></span>
        </div>
        <p>Больше</p>
      </div>

      <p v-if="error" class="mt-3 text-sm text-amber-400">{{ error }}</p>
    </div>
  </section>
</template>
