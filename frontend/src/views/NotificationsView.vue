<script setup>
import { computed, onMounted, ref } from 'vue'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const authStore = useAuthStore()

const offers = ref([])
const loading = ref(true)
const errorMessage = ref('')
const selectedOffer = ref(null)
const showConfirmModal = ref(false)
const confirmAction = ref(null)
const processingAction = ref(false)
const activeFilter = ref('all')

const filters = [
  { key: 'all', label: 'Все' },
  { key: 'new', label: 'Новые' },
  { key: 'pending', label: 'Ожидают ответа' },
  { key: 'accepted', label: 'Принятые' },
  { key: 'rejected', label: 'Отклонённые' },
]

const isUnread = (offer) => {
  if (authStore.isStudent) return !offer.is_read_by_student && offer.status === 'pending'
  if (authStore.isEmployer) return !offer.is_read_by_employer && offer.status !== 'pending'
  return false
}

const needsStudentAnswer = (offer) => authStore.isStudent && offer.is_read_by_student && offer.status === 'pending'

const statusMeta = (status) => {
  if (status === 'accepted') {
    return { label: 'Принято', dot: 'bg-emerald-400', badge: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' }
  }
  if (status === 'rejected') {
    return { label: 'Отклонено', dot: 'bg-rose-400', badge: 'border-rose-400/30 bg-rose-400/10 text-rose-300' }
  }
  return { label: 'Ожидает ответа', dot: 'bg-amber-300', badge: 'border-amber-300/30 bg-amber-300/10 text-amber-200' }
}

const fetchOffers = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const url = authStore.isStudent ? '/student/offers/' : '/employer/offers/'
    const res = await api.get(url)
    offers.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('Ошибка загрузки уведомлений:', e)
    errorMessage.value = 'Не удалось загрузить уведомления. Проверьте подключение и попробуйте ещё раз.'
  } finally {
    loading.value = false
  }
}

const openOffer = async (offer) => {
  selectedOffer.value = offer

  if (!isUnread(offer)) return

  try {
    const payload = authStore.isStudent
      ? { is_read_by_student: true }
      : { is_read_by_employer: true }

    await api.patch(`/offers/${offer.id}/update/`, payload)
    await fetchOffers()
    selectedOffer.value = offers.value.find((item) => item.id === offer.id) || offer
    window.dispatchEvent(new CustomEvent('update-bell'))
  } catch (e) {
    console.error('Ошибка обновления статуса прочтения:', e)
  }
}

const askAction = (action) => {
  confirmAction.value = action
  showConfirmModal.value = true
}

const handleAction = async () => {
  if (!selectedOffer.value || !confirmAction.value || processingAction.value) return

  processingAction.value = true
  try {
    await api.patch(`/offers/${selectedOffer.value.id}/update/`, { status: confirmAction.value })
    showConfirmModal.value = false

    const offerId = selectedOffer.value.id
    await fetchOffers()
    selectedOffer.value = offers.value.find((item) => item.id === offerId) || null
    window.dispatchEvent(new CustomEvent('update-bell'))
    showSuccess(confirmAction.value === 'accepted' ? 'Предложение принято.' : 'Предложение отклонено.')
  } catch (e) {
    console.error('Ошибка обновления предложения:', e)
    showError('Не удалось обновить статус предложения.')
  } finally {
    processingAction.value = false
  }
}

const getContactLink = (offer) => {
  if (!offer?.contact_link) return '#'

  const text = encodeURIComponent(
    `Здравствуйте! Я принял ваше приглашение на платформе ELCOURSE. Мой ник: ${offer.student_name || ''}. Давайте обсудим детали.`
  )

  const separator = offer.contact_link.includes('?') ? '&' : '?'
  return `${offer.contact_link}${separator}text=${text}`
}

const closeModal = () => {
  selectedOffer.value = null
  showConfirmModal.value = false
  confirmAction.value = null
}

const offerTitle = (offer) => {
  if (authStore.isStudent) return `Приглашение от ${offer.employer_name || 'работодателя'}`
  return `Предложение для ${offer.student_name || 'кандидата'}`
}

const offerPersonName = (offer) => authStore.isStudent ? offer.employer_name : offer.student_name
const offerPersonRole = computed(() => authStore.isStudent ? 'Работодатель' : 'Студент')

const formatDate = (value) => {
  if (!value) return 'Дата не указана'
  return new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}

const formatDateTime = (value) => {
  if (!value) return 'Дата не указана'
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const unreadCount = computed(() => offers.value.filter(isUnread).length)
const pendingCount = computed(() => offers.value.filter((offer) => offer.status === 'pending').length)
const acceptedCount = computed(() => offers.value.filter((offer) => offer.status === 'accepted').length)

const filteredOffers = computed(() => {
  if (activeFilter.value === 'new') return offers.value.filter(isUnread)
  if (activeFilter.value === 'pending') return offers.value.filter((offer) => offer.status === 'pending')
  if (activeFilter.value === 'accepted') return offers.value.filter((offer) => offer.status === 'accepted')
  if (activeFilter.value === 'rejected') return offers.value.filter((offer) => offer.status === 'rejected')
  return offers.value
})

onMounted(fetchOffers)
</script>

<template>
  <div class="mx-auto mt-8 max-w-5xl space-y-6 px-4 pb-12">
    <section class="rounded-[28px] border border-slate-700/60 bg-slate-900/55 p-6 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.28em] text-indigo-300">Карьерный контур</p>
          <h1 class="mt-2 text-3xl font-black text-slate-100">Уведомления</h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-400">
            Здесь отображаются карьерные предложения и ответы по ним. Новые события выделяются отдельно.
          </p>
        </div>

        <button
          type="button"
          class="inline-flex items-center justify-center rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-indigo-400 hover:text-white"
          @click="fetchOffers"
        >
          Обновить
        </button>
      </div>

      <div class="mt-6 grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Новые</p>
          <p class="mt-2 text-2xl font-black text-white">{{ unreadCount }}</p>
        </div>
        <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Ожидают</p>
          <p class="mt-2 text-2xl font-black text-white">{{ pendingCount }}</p>
        </div>
        <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Принятые</p>
          <p class="mt-2 text-2xl font-black text-white">{{ acceptedCount }}</p>
        </div>
      </div>
    </section>

    <section class="rounded-[28px] border border-slate-700/60 bg-slate-900/55 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-wrap gap-2 border-b border-slate-700/60 p-4">
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          class="rounded-2xl px-4 py-2 text-sm font-bold transition"
          :class="activeFilter === filter.key
            ? 'bg-indigo-600 text-white'
            : 'border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }}
        </button>
      </div>

      <div v-if="loading" class="flex h-64 flex-col items-center justify-center gap-3 text-slate-400">
        <div class="h-9 w-9 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent"></div>
        <p class="text-sm">Загружаем уведомления...</p>
      </div>

      <div v-else-if="errorMessage" class="p-6">
        <div class="rounded-3xl border border-rose-400/30 bg-rose-400/10 p-6 text-center">
          <h2 class="text-lg font-bold text-rose-200">Не удалось загрузить данные</h2>
          <p class="mt-2 text-sm text-rose-100/70">{{ errorMessage }}</p>
          <button
            type="button"
            class="mt-5 rounded-2xl bg-rose-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-rose-400"
            @click="fetchOffers"
          >
            Повторить
          </button>
        </div>
      </div>

      <div v-else-if="!filteredOffers.length" class="p-6">
        <div class="rounded-3xl border border-dashed border-slate-700 p-10 text-center">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/40 text-slate-500">
            <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11Z" />
              <path d="M8 9h8M8 13h5" />
            </svg>
          </div>
          <h2 class="mt-4 text-lg font-bold text-slate-200">Уведомлений пока нет</h2>
          <p class="mt-2 text-sm text-slate-500">Когда появятся предложения или ответы, они будут отображаться здесь.</p>
        </div>
      </div>

      <div v-else class="divide-y divide-slate-800/90">
        <button
          v-for="offer in filteredOffers"
          :key="offer.id"
          type="button"
          class="block w-full p-4 text-left transition hover:bg-slate-950/25 sm:p-5"
          :class="isUnread(offer) ? 'bg-indigo-500/10' : ''"
          @click="openOffer(offer)"
        >
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex min-w-0 gap-4">
              <div class="relative h-12 w-12 shrink-0 rounded-2xl border border-slate-700 bg-slate-950/50 text-slate-300">
                <div class="flex h-full w-full items-center justify-center text-lg font-black">
                  {{ offerPersonName(offer)?.[0]?.toUpperCase() || '?' }}
                </div>
                <span v-if="isUnread(offer)" class="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-indigo-400 ring-4 ring-slate-900"></span>
              </div>

              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-bold text-slate-100">{{ offerTitle(offer) }}</h3>
                  <span
                    class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-bold"
                    :class="statusMeta(offer.status).badge"
                  >
                    <span class="h-1.5 w-1.5 rounded-full" :class="statusMeta(offer.status).dot"></span>
                    {{ statusMeta(offer.status).label }}
                  </span>
                  <span v-if="needsStudentAnswer(offer)" class="rounded-full border border-amber-300/30 bg-amber-300/10 px-2.5 py-1 text-[11px] font-bold text-amber-200">
                    нужен ответ
                  </span>
                </div>

                <p class="mt-2 line-clamp-2 max-w-2xl text-sm leading-6 text-slate-400">
                  {{ offer.message || 'Сообщение не указано.' }}
                </p>
              </div>
            </div>

            <div class="shrink-0 text-left sm:text-right">
              <p class="text-xs font-semibold text-slate-400">{{ formatDate(offer.created_at) }}</p>
              <p v-if="isUnread(offer)" class="mt-1 text-xs font-bold text-indigo-300">новое событие</p>
            </div>
          </div>
        </button>
      </div>
    </section>

    <div
      v-if="selectedOffer"
      class="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      @click.self="closeModal"
    >
      <div class="max-h-[90vh] w-full max-w-xl overflow-hidden rounded-[28px] border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950/50">
        <div class="flex items-start justify-between gap-4 border-b border-slate-700/70 p-5">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-indigo-300">Детали предложения</p>
            <h2 class="mt-2 text-2xl font-black text-white">{{ offerTitle(selectedOffer) }}</h2>
          </div>
          <button
            type="button"
            class="rounded-2xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-400 transition hover:border-slate-500 hover:text-white"
            @click="closeModal"
          >
            Закрыть
          </button>
        </div>

        <div class="max-h-[calc(90vh-170px)] space-y-5 overflow-y-auto p-5">
          <div class="flex items-center gap-3 rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
            <div class="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-lg font-black text-slate-300">
              {{ offerPersonName(selectedOffer)?.[0]?.toUpperCase() || '?' }}
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ offerPersonRole }}</p>
              <p class="font-bold text-slate-100">{{ offerPersonName(selectedOffer) || 'Не указано' }}</p>
            </div>
          </div>

          <div>
            <p class="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Сообщение</p>
            <div class="whitespace-pre-wrap rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4 text-sm leading-6 text-slate-200">
              {{ selectedOffer.message || 'Нет текста сообщения.' }}
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Дата</p>
              <p class="mt-2 text-sm text-slate-200">{{ formatDateTime(selectedOffer.created_at) }}</p>
            </div>
            <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Статус</p>
              <span class="mt-2 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold" :class="statusMeta(selectedOffer.status).badge">
                <span class="h-1.5 w-1.5 rounded-full" :class="statusMeta(selectedOffer.status).dot"></span>
                {{ statusMeta(selectedOffer.status).label }}
              </span>
            </div>
          </div>

          <div v-if="selectedOffer.status === 'accepted' && authStore.isEmployer" class="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4">
            <p class="font-bold text-emerald-200">Студент принял ваше предложение.</p>
            <p class="mt-1 text-sm text-emerald-100/70">Ожидайте сообщения от кандидата по указанным контактам.</p>
          </div>
        </div>

        <div class="border-t border-slate-700/70 p-5">
          <div v-if="selectedOffer.status === 'pending' && authStore.isStudent" class="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              class="rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-500"
              @click="askAction('accepted')"
            >
              Принять предложение
            </button>
            <button
              type="button"
              class="rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300 transition hover:border-rose-400/50 hover:text-rose-300"
              @click="askAction('rejected')"
            >
              Отклонить
            </button>
          </div>

          <div v-else-if="selectedOffer.status === 'accepted' && authStore.isStudent" class="space-y-3">
            <a
              :href="getContactLink(selectedOffer)"
              target="_blank"
              rel="noopener noreferrer"
              class="block rounded-2xl bg-indigo-600 px-5 py-3 text-center text-sm font-bold text-white transition hover:bg-indigo-500"
            >
              Написать работодателю
            </a>
            <p class="text-center text-xs text-slate-500">Вы приняли предложение. Свяжитесь с работодателем для обсуждения деталей.</p>
          </div>

          <button
            v-else
            type="button"
            class="w-full rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
            @click="closeModal"
          >
            Понятно
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showConfirmModal"
      class="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/90 p-4 backdrop-blur-sm"
      @click.self="showConfirmModal = false"
    >
      <div class="w-full max-w-sm rounded-[28px] border border-slate-700 bg-slate-900 p-6 text-center shadow-2xl shadow-slate-950/50">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-amber-300/30 bg-amber-300/10 text-amber-200">
          <svg viewBox="0 0 24 24" class="h-7 w-7" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M12 8v5" />
            <path d="M12 17h.01" />
            <path d="M10.3 4.3 2.8 17.2A2 2 0 0 0 4.5 20h15a2 2 0 0 0 1.7-2.8L13.7 4.3a2 2 0 0 0-3.4 0Z" />
          </svg>
        </div>
        <h3 class="mt-4 text-xl font-black text-white">
          {{ confirmAction === 'accepted' ? 'Принять предложение?' : 'Отклонить предложение?' }}
        </h3>
        <p class="mt-2 text-sm leading-6 text-slate-400">
          После подтверждения статус будет обновлён и станет виден второй стороне.
        </p>
        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            class="rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-500 disabled:opacity-60"
            :disabled="processingAction"
            @click="handleAction"
          >
            {{ processingAction ? 'Сохранение...' : 'Подтвердить' }}
          </button>
          <button
            type="button"
            class="rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
            :disabled="processingAction"
            @click="showConfirmModal = false"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
