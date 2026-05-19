<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import api from './api'
import AppFooter from './components/AppFooter.vue'
import AppMobileNav from './components/AppMobileNav.vue'
import ToastHost from './components/ToastHost.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const unreadCount = ref(0)
const isUserMenuOpen = ref(false)
const userMenuRef = ref(null)

const routeExists = (path) => router.getRoutes().some((item) => item.path === path)
const publicFooterRouteNames = new Set(['home', 'courses', 'vacancies', 'login', 'register', 'course-detail'])

const showPublicFooter = computed(() => publicFooterRouteNames.has(route.name))

const roleLabel = computed(() => {
  if (authStore.isTeacher) return 'Преподаватель'
  if (authStore.isEmployer) return 'Работодатель'
  if (authStore.isStudent) return 'Студент'
  return 'Пользователь'
})

const primaryNavigation = computed(() => {
  const links = [{ label: 'Главная', to: '/' }]

  if (!authStore.isAuthenticated) {
    links.push(
      { label: 'Курсы', to: '/courses' },
      { label: 'Вакансии', to: '/vacancies' },
    )

    return links.filter((item) => item.to === '/' || routeExists(item.to))
  }

  if (authStore.isStudent) {
    links.push(
      { label: 'Курсы', to: '/courses' },
      { label: 'Вакансии', to: '/vacancies' },
      { label: 'Комьюнити', to: '/community' },
    )
  } else if (authStore.isTeacher) {
    links.push(
      { label: 'Кабинет автора', to: '/teacher' },
      { label: 'Комьюнити', to: '/community' },
    )
  } else if (authStore.isEmployer) {
    links.push(
      { label: 'Кандидаты', to: '/employer' },
      { label: 'Вакансии', to: '/vacancies' },
    )
  } else {
    links.push({ label: 'Комьюнити', to: '/community' })
  }

  return links.filter((item) => item.to === '/' || routeExists(item.to))
})

const secondaryUserLinks = computed(() => {
  const links = [
   
    { label: 'Уведомления', to: '/notifications', badge: unreadCount.value },
  ]

  if (authStore.isStudent) {
    links.unshift({ label: 'Мои курсы', to: '/courses' })
  }

  if (authStore.isTeacher) {
    links.unshift({ label: 'Кабинет автора', to: '/teacher' })
  }

  if (authStore.isEmployer) {
    links.unshift({ label: 'Кандидаты', to: '/employer' })
  }

  return links.filter((item) => routeExists(item.to))
})

const isActiveRoute = (path) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

const navigationLinkClass = (path) => [
  'inline-flex items-center justify-center whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition-colors duration-200 lg:px-3.5 lg:py-1.5 lg:text-[13px] xl:px-4',
  isActiveRoute(path)
    ? 'bg-slate-800 text-white shadow-inner shadow-black/10'
    : 'text-slate-400 hover:bg-slate-800/70 hover:text-white',
]

const closeMenus = () => {
  isUserMenuOpen.value = false
}

const toggleUserMenu = () => {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

const checkNotifications = async () => {
  if (!authStore.isAuthenticated) {
    unreadCount.value = 0
    return
  }

  try {
    const response = await api.get('/notifications/count/')
    unreadCount.value = response.data.unread_count || 0
  } catch (error) {
    console.error('Ошибка загрузки уведомлений:', error)
  }
}

const handleDocumentClick = (event) => {
  if (!isUserMenuOpen.value) return
  if (userMenuRef.value && !userMenuRef.value.contains(event.target)) {
    isUserMenuOpen.value = false
  }
}

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      checkNotifications()
    } else {
      unreadCount.value = 0
    }
  },
)

watch(
  () => route.fullPath,
  () => closeMenus(),
)

onMounted(async () => {
  await authStore.initialize()
  checkNotifications()
  window.addEventListener('update-bell', checkNotifications)
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('update-bell', checkNotifications)
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<template>
  <div class="flex min-h-screen flex-col bg-slate-900 pb-[calc(96px+env(safe-area-inset-bottom))] text-slate-300 selection:bg-indigo-500/30 lg:pb-0">
    <ToastHost />

    <header class="sticky top-0 z-[60] border-b border-white/10 bg-slate-950/60 shadow-[0_14px_40px_rgba(2,6,23,0.3)] backdrop-blur-2xl md:border-slate-800 md:bg-slate-900/88 md:shadow-lg md:backdrop-blur-xl">
      <div class="mx-auto flex min-h-[76px] w-full max-w-[1180px] items-center justify-between gap-2 px-3 sm:gap-4 sm:px-6 lg:min-h-[64px] lg:gap-3 lg:px-8">
        <RouterLink to="/" class="group flex min-w-0 items-center gap-2 text-white sm:gap-3" @click="closeMenus">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500 text-sm font-black tracking-wide shadow-lg shadow-indigo-500/20 transition group-hover:bg-indigo-400 lg:h-9 lg:w-9 lg:text-[13px]">
            EL
          </div>
          <span class="text-xl font-black tracking-[0.16em] sm:text-2xl sm:tracking-[0.22em] lg:text-[1.35rem] lg:tracking-[0.18em]">COURSE</span>
        </RouterLink>

        <nav class="hidden items-center gap-1.5 lg:flex xl:gap-2" aria-label="Основная навигация">
          <RouterLink
            v-for="item in primaryNavigation"
            :key="item.to"
            :to="item.to"
            :class="navigationLinkClass(item.to)"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="flex shrink-0 items-center gap-2 sm:gap-3 lg:gap-2.5">
          <RouterLink
            v-if="!authStore.isAuthenticated"
            to="/login"
            class="hidden rounded-full bg-indigo-600 px-[1.125rem] py-2 text-[13px] font-bold text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-500 lg:inline-flex"
          >
            Вход / Регистрация
          </RouterLink>

          <RouterLink
            v-if="!authStore.isAuthenticated"
            to="/login"
            class="inline-flex min-h-[44px] items-center justify-center rounded-full border border-white/10 bg-slate-900/65 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-slate-950/20 backdrop-blur-xl transition hover:border-indigo-300/40 hover:bg-slate-900/80 lg:hidden"
            aria-label="Вход или регистрация"
          >
            Вход
          </RouterLink>

         <div v-else ref="userMenuRef" class="relative flex items-center gap-2 lg:block">
  <div class="hidden items-center gap-2.5 rounded-full border border-slate-700/70 bg-slate-800/55 px-2.5 py-1.5 shadow-[inset_0_2px_10px_rgba(0,0,0,0.3)] lg:flex">
    <div class="hidden items-center gap-1.5 pl-0.5 xl:flex">
      <span class="relative flex h-2.5 w-2.5">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
        <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
      </span>
      <span class="text-[13px] font-bold text-emerald-400">В сети</span>
    </div>

    <RouterLink
      to="/notifications"
      class="relative flex h-9 w-9 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-700/60 hover:text-indigo-300"
      aria-label="Уведомления"
    >
      <svg class="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <span
        v-if="unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-bold text-white shadow-lg"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </RouterLink>

    <button
      class="flex min-h-[40px] items-center gap-2 rounded-full p-1 text-left transition hover:bg-slate-700/60"
      type="button"
      aria-label="Меню пользователя"
      :aria-expanded="isUserMenuOpen"
      @click.stop="toggleUserMenu"
    >
      <span class="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-slate-600 bg-slate-900">
        <img
          v-if="authStore.displayAvatar"
          :src="authStore.displayAvatar"
          alt="Аватар пользователя"
          class="h-full w-full object-cover"
        >
        <span v-else class="text-[13px] font-black text-slate-200">{{ authStore.displayInitial }}</span>
      </span>
      <svg class="hidden h-3.5 w-3.5 text-slate-500 transition sm:block" :class="isUserMenuOpen ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  </div>

  <RouterLink
    v-if="routeExists('/notifications')"
    to="/notifications"
    class="relative inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full border border-white/10 bg-slate-900/65 p-2 text-slate-200 shadow-lg shadow-slate-950/20 backdrop-blur-xl transition hover:border-indigo-300/40 hover:bg-slate-900/80 lg:hidden"
    aria-label="Уведомления"
  >
    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
    <span
      v-if="unreadCount > 0"
      class="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-500 px-1 text-[11px] font-bold text-white shadow-lg"
    >
      {{ unreadCount > 99 ? '99+' : unreadCount }}
    </span>
  </RouterLink>

  <button
    class="flex min-h-[44px] items-center justify-center rounded-full border border-white/10 bg-slate-900/65 p-1 text-left shadow-lg shadow-slate-950/20 backdrop-blur-xl transition hover:border-indigo-300/40 hover:bg-slate-900/80 lg:hidden"
    type="button"
    aria-label="Меню пользователя"
    :aria-expanded="isUserMenuOpen"
    @click.stop="toggleUserMenu"
  >
    <span class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-slate-600/80 bg-slate-900">
      <img
        v-if="authStore.displayAvatar"
        :src="authStore.displayAvatar"
        alt="Аватар пользователя"
        class="h-full w-full object-cover"
      >
      <span v-else class="text-sm font-black text-slate-200">{{ authStore.displayInitial }}</span>
    </span>
  </button>

  <transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="translate-y-2 opacity-0 scale-95"
    enter-to-class="translate-y-0 opacity-100 scale-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="translate-y-0 opacity-100 scale-100"
    leave-to-class="translate-y-2 opacity-0 scale-95"
  >
    <div
      v-if="isUserMenuOpen"
      class="absolute right-0 top-full z-[110] mt-3 min-w-[16rem] w-[min(18rem,calc(100vw-1.5rem))] max-w-[calc(100vw-1.5rem)] origin-top-right overflow-hidden rounded-3xl border border-white/[0.08] bg-[#0a0c10]/80 shadow-[0_40px_80px_-15px_rgba(0,0,0,0.7),inset_0_1px_0_rgba(255,255,255,0.1)] backdrop-blur-2xl"
    >
     <div class="relative overflow-hidden bg-indigo-500/[0.08] px-5 py-4">
        <p class="text-[15px] font-bold text-white">{{ authStore.user?.username || 'Аккаунт' }}</p>
        <p class="mt-0.5 text-[11px] font-bold uppercase tracking-[0.2em] text-indigo-300/80">{{ roleLabel }}</p>
      </div>

      <div class="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

      <div class="p-2.5 space-y-0.5">
        <RouterLink
          to="/profile"
          class="group flex min-h-[44px] items-center gap-3 rounded-2xl px-3 py-2 text-[14px] font-semibold text-slate-300 transition-all duration-200 hover:bg-white/[0.06] hover:text-white"
        >
          <svg class="h-4 w-4 text-slate-500 transition-colors group-hover:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Мой профиль
        </RouterLink>

        <RouterLink
          v-for="item in secondaryUserLinks"
          :key="item.to"
          :to="item.to"
          class="group flex min-h-[44px] items-center justify-between rounded-2xl px-3 py-2 text-[14px] font-semibold text-slate-300 transition-all duration-200 hover:bg-white/[0.06] hover:text-white"
        >
          <div class="flex items-center gap-3">
            <svg class="h-4 w-4 text-slate-500 transition-colors group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            <span>{{ item.label }}</span>
          </div>
          <span
            v-if="item.badge"
            class="flex h-5 items-center justify-center rounded-full bg-indigo-500/15 px-2 text-[11px] font-bold text-indigo-300"
          >
            {{ item.badge > 99 ? '99+' : item.badge }}
          </span>
        </RouterLink>

        <RouterLink
          to="/settings"
          class="group flex min-h-[44px] items-center gap-3 rounded-2xl px-3 py-2 text-[14px] font-semibold text-slate-300 transition-all duration-200 hover:bg-white/[0.06] hover:text-white"
        >
          <svg class="h-4 w-4 text-slate-500 transition-colors group-hover:text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Настройки
        </RouterLink>
      </div>

      <div class="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

      <div class="p-2">
        <button
          class="group flex min-h-[44px] w-full items-center justify-between rounded-2xl px-3 py-2 text-[14px] font-bold text-slate-300 transition-all duration-200 hover:bg-rose-500/10 hover:text-rose-400"
          type="button"
          @click="authStore.logout"
        >
          <div class="flex items-center gap-3">
            <svg class="h-4 w-4 text-slate-500 transition-colors group-hover:text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Выйти</span>
          </div>
        </button>
      </div>
    </div>
  </transition>
</div>

        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-7xl flex-1 px-3 py-6 sm:px-6 sm:py-8 lg:px-8">
      <RouterView v-slot="{ Component, route: currentRoute }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="currentRoute.fullPath" />
        </transition>
      </RouterView>
    </main>
    <AppFooter v-if="showPublicFooter" />
    <AppMobileNav :unread-count="unreadCount" />
  </div>
</template>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
  will-change: opacity, transform;
}

.page-enter-from,
.page-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition-duration: 1ms;
  }

  .page-enter-from,
  .page-leave-to {
    opacity: 1;
    transform: none;
  }
}
</style>
