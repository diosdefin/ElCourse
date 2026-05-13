<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const props = defineProps({
  unreadCount: {
    type: Number,
    default: 0,
  },
})

const authStore = useAuthStore()
const route = useRoute()

const navItems = computed(() => {
  if (!authStore.isAuthenticated) {
    return [
      { key: 'home', label: 'Главная', to: '/' },
      { key: 'courses', label: 'Курсы', to: '/courses' },
      { key: 'vacancies', label: 'Вакансии', to: '/vacancies' },
      { key: 'login', label: 'Вход', to: '/login' },
    ]
  }

  if (authStore.isTeacher) {
    return [
      { key: 'home', label: 'Главная', to: '/' },
      { key: 'community', label: 'Комьюнити', to: '/community' },
      { key: 'teacher', label: 'Кабинет', to: '/teacher', featured: true },
      { key: 'analytics', label: 'Аналитика', to: '/teacher/analytics' },
      { key: 'profile', label: 'Профиль', to: '/profile' },
    ]
  }

  if (authStore.isEmployer) {
    return [
      { key: 'home', label: 'Главная', to: '/' },
      { key: 'employer', label: 'Кандидаты', to: '/employer' },
      { key: 'vacancies', label: 'Вакансии', to: '/vacancies', featured: true },
      { key: 'notifications', label: 'Уведомления', to: '/notifications', badge: props.unreadCount },
      { key: 'profile', label: 'Профиль', to: '/profile' },
    ]
  }

  return [
    { key: 'home', label: 'Главная', to: '/' },
    { key: 'community', label: 'Комьюнити', to: '/community' },
    { key: 'courses', label: 'Курсы', to: '/courses', featured: true },
    { key: 'vacancies', label: 'Вакансии', to: '/vacancies' },
    { key: 'profile', label: 'Профиль', to: '/profile' },
  ]
})

const isItemActive = (key) => {
  const path = route.path

  if (key === 'home') return path === '/'
  if (key === 'courses') return path === '/courses' || path.startsWith('/course/')
  if (key === 'vacancies') return path === '/vacancies'
  if (key === 'login') return path === '/login' || path === '/register'
  if (key === 'notifications') return path === '/notifications'
  if (key === 'profile') return path === '/profile' || path === '/settings'
  if (key === 'community') return path === '/community'
  if (key === 'analytics') return path === '/teacher/analytics'
  if (key === 'employer') return path === '/employer'
  if (key === 'teacher') {
    return path === '/teacher' || (path.startsWith('/teacher/course/') && !path.startsWith('/teacher/analytics'))
  }

  return path === '/'
}

const itemClass = (item) => {
  const active = isItemActive(item.key)

  return [
    'relative flex min-h-[56px] min-w-0 flex-col items-center justify-center gap-1 rounded-[1.15rem] border px-2 py-2 text-[11px] font-semibold transition-all duration-200',
    active
      ? 'border-white/12 bg-white/12 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.18),inset_0_-10px_18px_rgba(15,23,42,0.18),0_12px_28px_rgba(2,6,23,0.28)]'
      : 'border-transparent bg-white/[0.02] text-slate-400 hover:bg-white/[0.06] hover:text-slate-100',
    item.featured
      ? active
        ? 'border-sky-200/20 bg-[linear-gradient(180deg,rgba(125,211,252,0.16),rgba(99,102,241,0.12))] shadow-[inset_0_1px_0_rgba(255,255,255,0.22),inset_0_-12px_18px_rgba(30,41,59,0.18),0_16px_32px_rgba(15,23,42,0.34)]'
        : 'border-sky-300/10 bg-[linear-gradient(180deg,rgba(125,211,252,0.08),rgba(99,102,241,0.05))] text-slate-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.10),0_12px_28px_rgba(2,6,23,0.22)] hover:border-sky-300/20 hover:bg-[linear-gradient(180deg,rgba(125,211,252,0.12),rgba(99,102,241,0.08))] hover:text-white'
      : '',
  ]
}
</script>

<template>
  <nav
    class="pointer-events-none fixed inset-x-0 bottom-0 z-[80] px-3 pb-3 pt-2 lg:hidden"
    :style="{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.75rem)' }"
    aria-label="Мобильная навигация"
  >
    <div
      class="pointer-events-auto relative mx-auto w-full max-w-7xl overflow-hidden rounded-[1.75rem] border border-white/10 bg-[rgba(2,6,23,0.86)] p-2 shadow-[0_-12px_40px_rgba(2,6,23,0.55),0_10px_28px_rgba(15,23,42,0.28)] backdrop-blur-[28px] [backdrop-filter:saturate(180%)_blur(28px)]"
    >
      <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent"></div>
      <div class="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/18 to-transparent"></div>
      <div class="grid gap-1.5" :style="{ gridTemplateColumns: `repeat(${navItems.length}, minmax(0, 1fr))` }">
        <RouterLink
          v-for="item in navItems"
          :key="item.key"
          :to="item.to"
          :aria-label="item.label"
          :title="item.label"
          :aria-current="isItemActive(item.key) ? 'page' : undefined"
          :class="itemClass(item)"
        >
          <span
            class="pointer-events-none absolute inset-x-4 top-0 h-0.5 rounded-full transition-opacity"
            :class="isItemActive(item.key)
              ? 'bg-sky-200 opacity-100 shadow-[0_0_12px_rgba(186,230,253,0.55)]'
              : item.featured
                ? 'bg-sky-200/50 opacity-60 shadow-[0_0_10px_rgba(186,230,253,0.18)]'
                : 'bg-transparent opacity-0'"
          ></span>

          <span class="relative flex h-6 w-6 items-center justify-center">
            <svg
              v-if="item.key === 'home'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 10.5 12 3l9 7.5V21H3z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 21v-6h6v6" />
            </svg>

            <svg
              v-else-if="item.key === 'courses'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6.5 12 3l8 3.5-8 3.5z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 10.5 12 14l8-3.5" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 14.5 12 18l8-3.5" />
            </svg>

            <svg
              v-else-if="item.key === 'vacancies'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4h5A1.5 1.5 0 0 1 16 5.5V7" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 8.5h16v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M10 12h4" />
            </svg>

            <svg
              v-else-if="item.key === 'notifications'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 0 0-4-5.7V5a2 2 0 1 0-4 0v.3A6 6 0 0 0 6 11v3.2c0 .5-.2 1-.6 1.4L4 17h5" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17a3 3 0 0 0 6 0" />
            </svg>

            <svg
              v-else-if="item.key === 'profile'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 20a7 7 0 0 1 14 0" />
            </svg>

            <svg
              v-else-if="item.key === 'analytics'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 19h16" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 15V9" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15V5" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 15v-3" />
            </svg>

            <svg
              v-else-if="item.key === 'community'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12a2.5 2.5 0 1 0-2.5-2.5A2.5 2.5 0 0 0 8 12Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 19a4 4 0 0 1 8 0" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 19a4 4 0 0 1 7 0" />
            </svg>

            <svg
              v-else-if="item.key === 'employer'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 12a2.5 2.5 0 1 0-2.5-2.5A2.5 2.5 0 0 0 7.5 12Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.5 19a4 4 0 0 1 8 0" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 19a4.5 4.5 0 0 1 9 0" />
            </svg>

            <svg
              v-else-if="item.key === 'teacher'"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6.5 12 3l8 3.5-8 3.5z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 10v4.5c0 1.5 2.2 3.5 5 3.5s5-2 5-3.5V10" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M20 8v5" />
            </svg>

            <svg
              v-else
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              aria-hidden="true"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 20a7 7 0 0 1 14 0" />
            </svg>

            <span
              v-if="item.badge"
              class="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold leading-none text-white shadow-lg shadow-rose-950/40"
            >
              {{ item.badge > 99 ? '99+' : item.badge }}
            </span>
          </span>

          <span class="truncate leading-none">{{ item.label }}</span>
        </RouterLink>
      </div>
    </div>
  </nav>
</template>
