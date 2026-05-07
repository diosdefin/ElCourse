<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const API_BASE_URL = 'http://127.0.0.1:8000'

const router = useRouter()
const authStore = useAuthStore()

const users = ref([])
const allSkills = ref([])
const myOffers = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const nextPageUrl = ref('')
const pageError = ref('')
const banner = ref({ type: '', message: '' })

const searchText = ref('')
const selectedSkills = ref([])
const friendLoadingUsername = ref('')

const offerModal = ref({
  isOpen: false,
  user: null,
  message: '',
  contact: '',
  submitting: false,
  error: '',
})

let searchTimer = null

const getAvatarUrl = (user) => {
  if (!user?.avatar) {
    return null
  }
  return user.avatar.startsWith('http') ? user.avatar : `${API_BASE_URL}${user.avatar}`
}

const parseListPayload = (payload) => {
  if (Array.isArray(payload)) {
    return { items: payload, next: '' }
  }
  return {
    items: payload?.results || [],
    next: payload?.next || '',
  }
}

const roleLabel = (role) => {
  if (role === 'student') return 'Студент'
  if (role === 'teacher') return 'Преподаватель'
  if (role === 'employer') return 'Работодатель'
  return 'Участник'
}

const skillSuggestions = computed(() => allSkills.value.slice(0, 14))

const latestOfferByStudentId = computed(() => {
  const mapped = new Map()
  for (const offer of myOffers.value) {
    if (!mapped.has(offer.student)) {
      mapped.set(offer.student, offer)
    }
  }
  return mapped
})

const getOfferStatusMeta = (user) => {
  if (!user || user.role !== 'student') {
    return null
  }
  const offer = latestOfferByStudentId.value.get(user.id)
  if (!offer) {
    return null
  }
  if (offer.status === 'pending') {
    return {
      text: 'Оффер отправлен',
      hint: 'Ожидает ответа',
      className: 'border-slate-700 bg-slate-950 text-slate-300',
    }
  }
  if (offer.status === 'accepted') {
    return {
      text: 'Оффер принят',
      hint: 'Повторно звать не нужно',
      className: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
    }
  }
  return null
}

const fetchSkills = async () => {
  try {
    const response = await api.get('/skills/')
    const { items } = parseListPayload(response.data)
    allSkills.value = items.sort((left, right) => left.name.localeCompare(right.name, 'ru'))
  } catch (error) {
    console.error('Ошибка загрузки навыков:', error)
  }
}

const fetchOffers = async () => {
  if (!authStore.isEmployer) {
    myOffers.value = []
    return
  }
  try {
    const response = await api.get('/employer/offers/')
    const { items } = parseListPayload(response.data)
    myOffers.value = items
  } catch (error) {
    console.error('Ошибка загрузки офферов:', error)
  }
}

const fetchUsers = async ({ reset = true } = {}) => {
  if (reset) {
    loading.value = true
    nextPageUrl.value = ''
  } else {
    loadingMore.value = true
  }
  pageError.value = ''

  try {
    const response = reset
      ? await api.get('/community/', {
          params: {
            search: searchText.value.trim() || undefined,
            skills: selectedSkills.value.join(',') || undefined,
          },
        })
      : await api.get(nextPageUrl.value)

    const { items, next } = parseListPayload(response.data)
    users.value = reset ? items : [...users.value, ...items]
    nextPageUrl.value = next
  } catch (error) {
    console.error('Ошибка загрузки сообщества:', error)
    pageError.value = 'Не удалось загрузить участников. Попробуйте обновить страницу.'
  } finally {
    if (reset) {
      loading.value = false
    } else {
      loadingMore.value = false
    }
  }
}

const loadMore = async () => {
  if (!nextPageUrl.value || loadingMore.value) {
    return
  }
  await fetchUsers({ reset: false })
}

const scheduleFetch = () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    fetchUsers({ reset: true })
  }, 250)
}

const isSelectedSkill = (skillName) =>
  selectedSkills.value.some((item) => item.toLowerCase() === skillName.toLowerCase())

const toggleSkill = (skillName) => {
  if (isSelectedSkill(skillName)) {
    selectedSkills.value = selectedSkills.value.filter((item) => item.toLowerCase() !== skillName.toLowerCase())
    return
  }
  selectedSkills.value = [...selectedSkills.value, skillName]
}

const clearFilters = () => {
  searchText.value = ''
  selectedSkills.value = []
}

const topSkills = (user) => (user.skills || []).slice(0, 3)

const openProfile = (user) => {
  router.push({ name: 'public-profile', params: { username: user.username } })
}

const applyUserPatch = (username, patch) => {
  users.value = users.value.map((user) => (user.username === username ? { ...user, ...patch } : user))
}

const toggleFriend = async (user) => {
  if (!authStore.isAuthenticated || !user || user.is_self) {
    return
  }
  friendLoadingUsername.value = user.username
  banner.value = { type: '', message: '' }

  try {
    const response = await api.post(`/users/${user.username}/friend/`, {})
    applyUserPatch(user.username, {
      is_friend: response.data.is_friend,
      friends_count: response.data.friends_count,
    })
    banner.value = { type: 'success', message: response.data.message }
    showSuccess(response.data.message)
  } catch (error) {
    const message = error.response?.data?.detail || 'Не удалось обновить список друзей.'
    banner.value = { type: 'error', message }
    showError(message)
  } finally {
    friendLoadingUsername.value = ''
  }
}

const openOfferModal = (user) => {
  if (!authStore.isEmployer || !user || getOfferStatusMeta(user)) {
    return
  }
  banner.value = { type: '', message: '' }
  offerModal.value = {
    isOpen: true,
    user,
    message: `Здравствуйте, ${user.username}! Нам понравился ваш профиль на ELCOURSE и мы хотели бы обсудить возможное сотрудничество.`,
    contact: '',
    submitting: false,
    error: '',
  }
}

const closeOfferModal = () => {
  offerModal.value = {
    isOpen: false,
    user: null,
    message: '',
    contact: '',
    submitting: false,
    error: '',
  }
}

const submitOffer = async () => {
  if (!offerModal.value.user || !offerModal.value.message.trim()) {
    return
  }
  offerModal.value.submitting = true
  offerModal.value.error = ''

  try {
    await api.post('/employer/offer/', {
      student_id: offerModal.value.user.id,
      message: offerModal.value.message.trim(),
      contact_link: offerModal.value.contact.trim(),
    })
    const invitedUsername = offerModal.value.user.username
    closeOfferModal()
    await fetchOffers()
    const message = `Оффер для ${invitedUsername} отправлен.`
    banner.value = { type: 'success', message }
    showSuccess(message)
  } catch (error) {
    offerModal.value.error =
      error.response?.data?.detail || 'Не удалось отправить оффер. Попробуйте еще раз.'
    showError(offerModal.value.error)
    if (error.response?.data?.existing_offer) {
      await fetchOffers()
    }
  } finally {
    offerModal.value.submitting = false
  }
}

watch([searchText, selectedSkills], scheduleFetch, { deep: true })

onMounted(async () => {
  await Promise.all([fetchSkills(), fetchUsers({ reset: true }), fetchOffers()])
})

onUnmounted(() => {
  window.clearTimeout(searchTimer)
})
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 pb-16">
    <section
      class="z-40 rounded-[2rem] border border-slate-800/80 bg-slate-950/75 p-4 shadow-[0_30px_80px_rgba(2,6,23,0.35)] backdrop-blur-xl sm:p-5"
    >
      <div class="flex flex-col gap-4">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.35em] text-slate-500">Community</p>
            <h1 class="mt-2 text-2xl font-black text-white sm:text-3xl">
              Единый поиск людей, навыков и карьерных сигналов
            </h1>
          </div>
          <div class="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3 text-right">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Найдено</p>
            <p class="mt-2 text-2xl font-black text-white">{{ users.length }}</p>
          </div>
        </div>

        <div class="rounded-[1.6rem] border border-slate-800 bg-slate-900/80 p-3">
          <div class="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3">
            <svg class="h-5 w-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35m1.85-5.15a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>

            <span
              v-for="skill in selectedSkills"
              :key="skill"
              class="inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-200"
            >
              {{ skill }}
              <button class="text-indigo-200 transition hover:text-white" @click="toggleSkill(skill)">×</button>
            </span>

            <input
              v-model="searchText"
              type="text"
              placeholder="Ищите по username или bio, навыки добавляйте тегами ниже"
              class="min-w-[220px] flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
            >

            <button
              v-if="searchText || selectedSkills.length"
              class="rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300 transition hover:border-slate-500 hover:text-white"
              @click="clearFilters"
            >
              Очистить
            </button>
          </div>

          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="skill in skillSuggestions"
              :key="skill.id"
              class="rounded-full border px-3 py-1.5 text-xs font-semibold transition"
              :class="isSelectedSkill(skill.name)
                ? 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300'
                : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500 hover:text-white'"
              @click="toggleSkill(skill.name)"
            >
              {{ skill.name }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div
      v-if="banner.message"
      class="rounded-2xl border px-4 py-3 text-sm font-medium"
      :class="banner.type === 'success'
        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
        : 'border-rose-500/20 bg-rose-500/10 text-rose-300'"
    >
      {{ banner.message }}
    </div>

    <div v-if="loading" class="rounded-[1.8rem] border border-slate-800 bg-slate-900/70 px-6 py-20 text-center text-slate-400">
      Загружаем участников сообщества...
    </div>

    <div
      v-else-if="pageError"
      class="rounded-[1.8rem] border border-rose-500/20 bg-rose-500/10 px-6 py-12 text-center text-rose-300"
    >
      {{ pageError }}
    </div>

    <div
      v-else-if="users.length === 0"
      class="rounded-[1.8rem] border border-dashed border-slate-700 bg-slate-900/50 px-6 py-20 text-center"
    >
      <p class="text-xl font-bold text-white">Совпадений пока нет</p>
      <p class="mt-3 text-sm text-slate-500">Попробуйте убрать часть тегов или расширить текстовый запрос.</p>
    </div>

    <section v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="user in users"
        :key="user.id"
        class="group cursor-pointer rounded-[1.7rem] border border-slate-800/80 bg-slate-900/75 p-5 transition duration-300 hover:-translate-y-1.5 hover:border-slate-600 hover:shadow-[0_25px_60px_rgba(2,6,23,0.32)]"
        tabindex="0"
        @click="openProfile(user)"
        @keydown.enter.prevent="openProfile(user)"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-center gap-4">
            <div class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 text-xl font-black text-slate-300">
              <img v-if="getAvatarUrl(user)" :src="getAvatarUrl(user)" :alt="user.username" class="h-full w-full object-cover">
              <span v-else>{{ user.username.charAt(0).toUpperCase() }}</span>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-xl font-black text-white">{{ user.username }}</h2>
                <span v-if="user.is_verified" class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-sky-500/10 text-xs font-bold text-sky-300">✓</span>
              </div>
              <p class="mt-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{{ roleLabel(user.role) }}</p>
            </div>
          </div>

          <span class="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
            {{ user.friends_count }} друзей
          </span>
        </div>

        <p class="mt-4 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-slate-300">
          {{ user.bio || 'Публичное описание пока пустое, но навыки и профиль уже доступны для просмотра.' }}
        </p>

        <div class="mt-4 flex flex-wrap gap-2">
          <span
            v-for="skill in topSkills(user)"
            :key="`${user.id}-${skill.id}`"
            class="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300"
          >
            {{ skill.name }}
          </span>
          <span
            v-if="(user.skills || []).length > 3"
            class="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-400"
          >
            +{{ user.skills.length - 3 }}
          </span>
        </div>

        <p v-if="user.common_friends_count" class="mt-4 text-sm font-medium text-slate-400">
          {{ user.common_friends_count }} общих друзей
        </p>

        <div class="mt-5 flex flex-wrap gap-3">
          <div
            v-if="authStore.isEmployer && getOfferStatusMeta(user)"
            class="rounded-2xl border px-4 py-3 text-sm font-semibold"
            :class="getOfferStatusMeta(user).className"
            @click.stop
          >
            <p>{{ getOfferStatusMeta(user).text }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ getOfferStatusMeta(user).hint }}</p>
          </div>

          <button
            v-else-if="authStore.isEmployer && user.role === 'student' && !user.is_self"
            class="rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-500"
            @click.stop="openOfferModal(user)"
          >
            Пригласить
          </button>

          <button
            v-else-if="authStore.isAuthenticated && !authStore.isEmployer && !user.is_self"
            class="rounded-2xl border px-4 py-3 text-sm font-bold transition"
            :class="user.is_friend
              ? 'border-rose-500/20 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20'
              : 'border-slate-700 bg-slate-950 text-slate-100 hover:border-slate-500'"
            :disabled="friendLoadingUsername === user.username"
            @click.stop="toggleFriend(user)"
          >
            {{ friendLoadingUsername === user.username ? 'Обновляем...' : (user.is_friend ? 'Удалить из друзей' : 'В друзья') }}
          </button>

          <div
            v-else-if="user.is_self"
            class="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-400"
            @click.stop
          >
            Это вы
          </div>

          <button
            class="rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
            @click.stop="openProfile(user)"
          >
            Профиль
          </button>
        </div>
      </article>
    </section>

    <div class="flex justify-center pt-3" v-if="nextPageUrl && users.length > 0">
      <button
        class="rounded-2xl border border-slate-700 bg-slate-900 px-5 py-2 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white disabled:opacity-60"
        :disabled="loadingMore"
        @click="loadMore"
      >
        {{ loadingMore ? 'Загружаем...' : 'Загрузить еще' }}
      </button>
    </div>

    <div
      v-if="offerModal.isOpen && offerModal.user"
      class="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/85 p-4 backdrop-blur-md"
      @click.self="closeOfferModal"
    >
      <div class="w-full max-w-2xl rounded-[2rem] border border-slate-700 bg-slate-900 p-8 shadow-2xl shadow-black/60">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300">Новый оффер</p>
            <h2 class="mt-3 text-3xl font-black text-white">Приглашение для {{ offerModal.user.username }}</h2>
            <p class="mt-3 text-sm leading-6 text-slate-400">
              После отправки карточка автоматически заблокирует повторный активный оффер и покажет статус.
            </p>
          </div>
          <button class="text-slate-500 transition hover:text-white" @click="closeOfferModal">
            <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="mt-8 space-y-5">
          <div>
            <label class="mb-2 block text-sm font-bold text-slate-300">Сообщение</label>
            <textarea
              v-model="offerModal.message"
              rows="5"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-5 py-4 text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
              placeholder="Расскажите, почему профиль заинтересовал вас и как можно связаться..."
            ></textarea>
          </div>

          <div>
            <label class="mb-2 block text-sm font-bold text-slate-300">Контакт</label>
            <input
              v-model="offerModal.contact"
              type="text"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-5 py-4 text-slate-100 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/30"
              placeholder="t.me/hr_manager или email@company.com"
            >
          </div>

          <div v-if="offerModal.error" class="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            {{ offerModal.error }}
          </div>
        </div>

        <div class="mt-8 grid gap-3 sm:grid-cols-2">
          <button
            class="rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
            @click="closeOfferModal"
          >
            Отмена
          </button>
          <button
            class="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="offerModal.submitting || !offerModal.message.trim()"
            @click="submitOffer"
          >
            {{ offerModal.submitting ? 'Отправляем...' : 'Отправить оффер' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
