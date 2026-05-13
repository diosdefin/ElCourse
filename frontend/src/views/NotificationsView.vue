<script setup>
import { computed, onMounted, ref } from 'vue'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const authStore = useAuthStore()

const offers = ref([])
const applications = ref([])
const loading = ref(true)
const errorMessage = ref('')
const selectedItem = ref(null)
const showConfirmModal = ref(false)
const confirmAction = ref(null)
const processingAction = ref(false)
const activeFilter = ref('all')

const filters = [
  { key: 'all', label: 'Все' },
  { key: 'new', label: 'Новые' },
  { key: 'offers', label: 'Предложения' },
  { key: 'applications', label: 'Отклики' },
  { key: 'pending', label: 'Ожидают' },
  { key: 'accepted', label: 'Принятые' },
  { key: 'rejected', label: 'Отклонённые' },
]

const statusMeta = (status) => {
  const map = {
    accepted: {
      label: 'Принято',
      tone: 'success',
      dot: 'bg-emerald-400',
      badge: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
    },
    rejected: {
      label: 'Отклонено',
      tone: 'danger',
      dot: 'bg-rose-400',
      badge: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
    },
    viewed: {
      label: 'Просмотрено',
      tone: 'info',
      dot: 'bg-sky-400',
      badge: 'border-sky-400/30 bg-sky-400/10 text-sky-300',
    },
    withdrawn: {
      label: 'Отозвано',
      tone: 'muted',
      dot: 'bg-slate-400',
      badge: 'border-slate-500/40 bg-slate-500/10 text-slate-300',
    },
    pending: {
      label: 'Ожидает ответа',
      tone: 'warning',
      dot: 'bg-amber-300',
      badge: 'border-amber-300/30 bg-amber-300/10 text-amber-200',
    },
  }

  return map[status] || map.pending
}

const normalizeOffer = (offer) => ({
  id: `offer-${offer.id}`,
  sourceId: offer.id,
  type: 'offer',
  sourceLabel: 'Прямое предложение',
  title: authStore.isStudent
    ? `Приглашение от ${offer.employer_name || 'работодателя'}`
    : `Предложение для ${offer.student_name || 'кандидата'}`,
  personName: authStore.isStudent ? offer.employer_name : offer.student_name,
  personRole: authStore.isStudent ? 'Работодатель' : 'Студент',
  message: offer.message || '',
  status: offer.status,
  createdAt: offer.created_at,
  updatedAt: offer.created_at,
  unread: authStore.isStudent
    ? !offer.is_read_by_student && offer.status === 'pending'
    : !offer.is_read_by_employer && offer.status !== 'pending',
  raw: offer,
})

const normalizeApplication = (application) => {
  const vacancy = application.vacancy || {}
  const company = vacancy.company_name || vacancy.employer_name || 'работодатель'

  return {
    id: `application-${application.id}`,
    sourceId: application.id,
    type: 'application',
    sourceLabel: 'Отклик на вакансию',
    title: authStore.isStudent
      ? `Отклик: ${vacancy.title || 'вакансия'}`
      : `Отклик от ${application.student_username || 'студента'}`,
    personName: authStore.isStudent ? company : application.student_username,
    personRole: authStore.isStudent ? 'Компания' : 'Студент',
    message: application.message || '',
    status: application.status,
    createdAt: application.created_at,
    updatedAt: application.updated_at,
    unread: authStore.isStudent ? !application.is_read_by_student : !application.is_read_by_employer,
    raw: application,
  }
}

const notifications = computed(() => {
  const directOffers = offers.value.map(normalizeOffer)
  const vacancyApplications = applications.value.map(normalizeApplication)

  return [...directOffers, ...vacancyApplications].sort((a, b) => {
    const bDate = new Date(b.updatedAt || b.createdAt || 0).getTime()
    const aDate = new Date(a.updatedAt || a.createdAt || 0).getTime()
    return bDate - aDate
  })
})

const unreadCount = computed(() => notifications.value.filter((item) => item.unread).length)
const pendingCount = computed(() => notifications.value.filter((item) => item.status === 'pending' || item.status === 'viewed').length)
const acceptedCount = computed(() => notifications.value.filter((item) => item.status === 'accepted').length)
const applicationCount = computed(() => applications.value.length)

const filteredNotifications = computed(() => {
  if (activeFilter.value === 'new') return notifications.value.filter((item) => item.unread)
  if (activeFilter.value === 'offers') return notifications.value.filter((item) => item.type === 'offer')
  if (activeFilter.value === 'applications') return notifications.value.filter((item) => item.type === 'application')
  if (activeFilter.value === 'pending') return notifications.value.filter((item) => item.status === 'pending' || item.status === 'viewed')
  if (activeFilter.value === 'accepted') return notifications.value.filter((item) => item.status === 'accepted')
  if (activeFilter.value === 'rejected') return notifications.value.filter((item) => item.status === 'rejected' || item.status === 'withdrawn')
  return notifications.value
})

const fetchNotifications = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    if (authStore.isStudent) {
      const [offersRes, applicationsRes] = await Promise.all([
        api.get('/student/offers/'),
        api.get('/student/vacancy-applications/'),
      ])
      offers.value = Array.isArray(offersRes.data) ? offersRes.data : []
      applications.value = Array.isArray(applicationsRes.data) ? applicationsRes.data : []
    } else if (authStore.isEmployer) {
      const [offersRes, applicationsRes] = await Promise.all([
        api.get('/employer/offers/'),
        api.get('/employer/vacancy-applications/'),
      ])
      offers.value = Array.isArray(offersRes.data) ? offersRes.data : []
      applications.value = Array.isArray(applicationsRes.data) ? applicationsRes.data : []
    } else {
      offers.value = []
      applications.value = []
    }
  } catch (error) {
    console.error('Ошибка загрузки уведомлений:', error)
    errorMessage.value = 'Не удалось загрузить уведомления. Проверьте подключение и попробуйте ещё раз.'
  } finally {
    loading.value = false
  }
}

const updateBell = () => {
  window.dispatchEvent(new CustomEvent('update-bell'))
}

const readEndpoint = (item) => {
  if (item.type === 'offer') return `/offers/${item.sourceId}/update/`
  if (authStore.isStudent) return `/student/vacancy-applications/${item.sourceId}/`
  return `/employer/vacancy-applications/${item.sourceId}/`
}

const markAsRead = async (item) => {
  if (!item?.unread) return

  const payload = authStore.isStudent
    ? { is_read_by_student: true }
    : { is_read_by_employer: true }

  await api.patch(readEndpoint(item), payload)
}

const openNotification = async (item) => {
  selectedItem.value = item

  if (!item.unread) return

  try {
    await markAsRead(item)
    await fetchNotifications()
    selectedItem.value = notifications.value.find((notification) => notification.id === item.id) || item
    updateBell()
  } catch (error) {
    console.error('Ошибка обновления статуса прочтения:', error)
  }
}

const askAction = (action) => {
  confirmAction.value = action
  showConfirmModal.value = true
}

const handleAction = async () => {
  if (!selectedItem.value || !confirmAction.value || processingAction.value) return

  processingAction.value = true
  const current = selectedItem.value

  try {
    if (current.type === 'offer') {
      await api.patch(`/offers/${current.sourceId}/update/`, { status: confirmAction.value })
    } else if (authStore.isStudent) {
      await api.patch(`/student/vacancy-applications/${current.sourceId}/`, { status: confirmAction.value })
    } else if (authStore.isEmployer) {
      await api.patch(`/employer/vacancy-applications/${current.sourceId}/`, { status: confirmAction.value })
    }

    showConfirmModal.value = false
    await fetchNotifications()
    selectedItem.value = notifications.value.find((notification) => notification.id === current.id) || null
    updateBell()

    const messages = {
      accepted: current.type === 'application' ? 'Отклик принят.' : 'Предложение принято.',
      rejected: current.type === 'application' ? 'Отклик отклонён.' : 'Предложение отклонено.',
      viewed: 'Отклик отмечен как просмотренный.',
      withdrawn: 'Отклик отозван.',
    }
    showSuccess(messages[confirmAction.value] || 'Статус обновлён.')
  } catch (error) {
    console.error('Ошибка обновления уведомления:', error)
    showError(error?.response?.data?.detail || 'Не удалось обновить статус.')
  } finally {
    processingAction.value = false
  }
}

const getContactLink = (item) => {
  const offer = item?.raw
  if (!offer?.contact_link) return '#'

  const text = encodeURIComponent(
    `Здравствуйте! Я принял ваше приглашение на платформе ELCOURSE. Мой ник: ${offer.student_name || ''}. Давайте обсудим детали.`
  )

  const separator = offer.contact_link.includes('?') ? '&' : '?'
  return `${offer.contact_link}${separator}text=${text}`
}

const canStudentAnswerOffer = (item) => authStore.isStudent && item?.type === 'offer' && item.status === 'pending'
const canStudentContactEmployer = (item) => authStore.isStudent && item?.type === 'offer' && item.status === 'accepted'
const canEmployerProcessApplication = (item) => authStore.isEmployer && item?.type === 'application' && !['accepted', 'rejected', 'withdrawn'].includes(item.status)
const canStudentWithdrawApplication = (item) => authStore.isStudent && item?.type === 'application' && ['pending', 'viewed'].includes(item.status)

const closeModal = () => {
  selectedItem.value = null
  showConfirmModal.value = false
  confirmAction.value = null
}

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

const initials = (value) => String(value || '?').charAt(0).toUpperCase()

const applicationVacancy = computed(() => selectedItem.value?.type === 'application' ? selectedItem.value.raw?.vacancy || {} : {})

const confirmTitle = computed(() => {
  const action = confirmAction.value
  if (action === 'accepted') return selectedItem.value?.type === 'application' ? 'Принять отклик?' : 'Принять предложение?'
  if (action === 'rejected') return selectedItem.value?.type === 'application' ? 'Отклонить отклик?' : 'Отклонить предложение?'
  if (action === 'viewed') return 'Отметить отклик просмотренным?'
  if (action === 'withdrawn') return 'Отозвать отклик?'
  return 'Подтвердить действие?'
})

onMounted(fetchNotifications)
</script>

<template>
  <div class="mx-auto mt-8 max-w-6xl space-y-6 px-4 pb-12">
    <section class="rounded-[28px] border border-slate-700/60 bg-slate-900/55 p-6 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.28em] text-sky-300">Карьерный контур</p>
          <h1 class="mt-2 text-3xl font-black text-slate-100">Уведомления</h1>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Здесь собраны прямые предложения работодателей, отклики на вакансии и изменения их статусов.
          </p>
        </div>

        <button
          type="button"
          class="inline-flex items-center justify-center rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-sky-400 hover:text-white"
          @click="fetchNotifications"
        >
          Обновить
        </button>
      </div>

      <div class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
        <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
          <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Отклики</p>
          <p class="mt-2 text-2xl font-black text-white">{{ applicationCount }}</p>
        </div>
      </div>
    </section>

    <section class="overflow-hidden rounded-[28px] border border-slate-700/60 bg-slate-900/55 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-wrap gap-2 border-b border-slate-700/60 p-4">
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          class="rounded-2xl px-4 py-2 text-sm font-bold transition"
          :class="activeFilter === filter.key
            ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/20'
            : 'border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200'"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }}
        </button>
      </div>

      <div v-if="loading" class="flex h-64 flex-col items-center justify-center gap-3 text-slate-400">
        <div class="h-9 w-9 animate-spin rounded-full border-2 border-sky-400 border-t-transparent"></div>
        <p class="text-sm">Загружаем уведомления...</p>
      </div>

      <div v-else-if="errorMessage" class="p-6">
        <div class="rounded-3xl border border-rose-400/30 bg-rose-400/10 p-6 text-center">
          <h2 class="text-lg font-bold text-rose-200">Не удалось загрузить данные</h2>
          <p class="mt-2 text-sm text-rose-100/70">{{ errorMessage }}</p>
          <button
            type="button"
            class="mt-5 rounded-2xl bg-rose-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-rose-400"
            @click="fetchNotifications"
          >
            Повторить
          </button>
        </div>
      </div>

      <div v-else-if="!filteredNotifications.length" class="p-6">
        <div class="rounded-3xl border border-dashed border-slate-700 p-10 text-center">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/40 text-slate-500">
            <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11Z" />
              <path d="M8 9h8M8 13h5" />
            </svg>
          </div>
          <h2 class="mt-4 text-lg font-bold text-slate-200">Уведомлений пока нет</h2>
          <p class="mt-2 text-sm text-slate-500">Когда появятся предложения, отклики или ответы, они будут отображаться здесь.</p>
        </div>
      </div>

      <div v-else class="divide-y divide-slate-800/90">
        <button
          v-for="item in filteredNotifications"
          :key="item.id"
          type="button"
          class="block w-full p-4 text-left transition hover:bg-slate-950/25 sm:p-5"
          :class="item.unread ? 'bg-sky-500/10' : ''"
          @click="openNotification(item)"
        >
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex min-w-0 gap-4">
              <div class="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/50 text-lg font-black text-slate-300">
                {{ initials(item.personName) }}
                <span v-if="item.unread" class="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-sky-400 ring-4 ring-slate-900"></span>
              </div>

              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-full border border-slate-700 bg-slate-950/50 px-2.5 py-1 text-[11px] font-bold text-slate-400">
                    {{ item.sourceLabel }}
                  </span>
                  <span
                    class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-bold"
                    :class="statusMeta(item.status).badge"
                  >
                    <span class="h-1.5 w-1.5 rounded-full" :class="statusMeta(item.status).dot"></span>
                    {{ statusMeta(item.status).label }}
                  </span>
                  <span v-if="item.unread" class="rounded-full border border-sky-300/30 bg-sky-300/10 px-2.5 py-1 text-[11px] font-bold text-sky-200">
                    новое
                  </span>
                </div>

                <h3 class="mt-2 font-bold text-slate-100">{{ item.title }}</h3>
                <p class="mt-1 text-xs text-slate-500">{{ item.personRole }} · {{ item.personName || 'не указано' }}</p>
                <p class="mt-2 line-clamp-2 max-w-2xl text-sm leading-6 text-slate-400">
                  {{ item.message || (item.type === 'application' ? 'Отклик отправлен без сопроводительного сообщения.' : 'Сообщение не указано.') }}
                </p>
              </div>
            </div>

            <div class="shrink-0 text-left sm:text-right">
              <p class="text-xs font-semibold text-slate-400">{{ formatDate(item.updatedAt || item.createdAt) }}</p>
              <p v-if="item.unread" class="mt-1 text-xs font-bold text-sky-300">новое событие</p>
            </div>
          </div>
        </button>
      </div>
    </section>

    <div
      v-if="selectedItem"
      class="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      @click.self="closeModal"
    >
      <div class="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-[28px] border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950/50">
        <div class="flex items-start justify-between gap-4 border-b border-slate-700/70 p-5">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-sky-300">{{ selectedItem.sourceLabel }}</p>
            <h2 class="mt-2 text-2xl font-black text-white">{{ selectedItem.title }}</h2>
          </div>
          <button
            type="button"
            class="rounded-2xl border border-slate-700 px-3 py-2 text-sm font-bold text-slate-400 transition hover:border-slate-500 hover:text-white"
            @click="closeModal"
          >
            Закрыть
          </button>
        </div>

        <div class="max-h-[calc(90vh-180px)] space-y-5 overflow-y-auto p-5">
          <div class="flex items-center gap-3 rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
            <div class="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 text-lg font-black text-slate-300">
              {{ initials(selectedItem.personName) }}
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ selectedItem.personRole }}</p>
              <p class="font-bold text-slate-100">{{ selectedItem.personName || 'Не указано' }}</p>
            </div>
          </div>

          <div v-if="selectedItem.type === 'application'" class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
            <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Вакансия</p>
            <h3 class="mt-2 text-lg font-black text-slate-100">{{ applicationVacancy.title || 'Вакансия' }}</h3>
            <p class="mt-1 text-sm text-slate-400">{{ applicationVacancy.company_name || applicationVacancy.employer_name || 'Компания не указана' }}</p>
            <div v-if="applicationVacancy.skills?.length" class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="skill in applicationVacancy.skills"
                :key="skill.id"
                class="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-xs font-bold text-sky-200"
              >
                {{ skill.name }}
              </span>
            </div>
          </div>

          <div>
            <p class="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
              {{ selectedItem.type === 'application' ? 'Сопроводительное сообщение' : 'Сообщение' }}
            </p>
            <div class="whitespace-pre-wrap rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4 text-sm leading-6 text-slate-200">
              {{ selectedItem.message || (selectedItem.type === 'application' ? 'Отклик отправлен без сопроводительного сообщения.' : 'Нет текста сообщения.') }}
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Дата события</p>
              <p class="mt-2 text-sm text-slate-200">{{ formatDateTime(selectedItem.updatedAt || selectedItem.createdAt) }}</p>
            </div>
            <div class="rounded-2xl border border-slate-700/70 bg-slate-950/35 p-4">
              <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Статус</p>
              <span class="mt-2 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold" :class="statusMeta(selectedItem.status).badge">
                <span class="h-1.5 w-1.5 rounded-full" :class="statusMeta(selectedItem.status).dot"></span>
                {{ statusMeta(selectedItem.status).label }}
              </span>
            </div>
          </div>

          <div v-if="selectedItem.type === 'application' && selectedItem.status === 'accepted' && authStore.isStudent" class="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4">
            <p class="font-bold text-emerald-200">Ваш отклик принят.</p>
            <p class="mt-1 text-sm text-emerald-100/70">Работодатель заинтересовался вашим профилем. Проверьте контакты вакансии или ожидайте связи.</p>
          </div>

          <div v-if="selectedItem.type === 'application' && selectedItem.status === 'accepted' && authStore.isEmployer" class="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4">
            <p class="font-bold text-emerald-200">Отклик принят.</p>
            <p class="mt-1 text-sm text-emerald-100/70">Студент увидит обновлённый статус в уведомлениях.</p>
          </div>
        </div>

        <div class="border-t border-slate-700/70 p-5">
          <div v-if="canStudentAnswerOffer(selectedItem)" class="grid gap-3 sm:grid-cols-2">
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

          <div v-else-if="canEmployerProcessApplication(selectedItem)" class="grid gap-3 sm:grid-cols-3">
            <button
              v-if="selectedItem.status === 'pending'"
              type="button"
              class="rounded-2xl border border-sky-400/40 bg-sky-400/10 px-5 py-3 text-sm font-bold text-sky-200 transition hover:bg-sky-500 hover:text-white"
              @click="askAction('viewed')"
            >
              Просмотрено
            </button>
            <button
              type="button"
              class="rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-emerald-500"
              @click="askAction('accepted')"
            >
              Принять
            </button>
            <button
              type="button"
              class="rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300 transition hover:border-rose-400/50 hover:text-rose-300"
              @click="askAction('rejected')"
            >
              Отклонить
            </button>
          </div>

          <div v-else-if="canStudentWithdrawApplication(selectedItem)" class="grid gap-3 sm:grid-cols-[1fr_auto]">
            <RouterLink
              to="/vacancies"
              class="rounded-2xl border border-slate-700 px-5 py-3 text-center text-sm font-bold text-slate-300 transition hover:border-sky-400/50 hover:text-sky-200"
            >
              Открыть вакансии
            </RouterLink>
            <button
              type="button"
              class="rounded-2xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-300 transition hover:border-rose-400/50 hover:text-rose-300"
              @click="askAction('withdrawn')"
            >
              Отозвать отклик
            </button>
          </div>

          <div v-else-if="canStudentContactEmployer(selectedItem)" class="space-y-3">
            <a
              :href="getContactLink(selectedItem)"
              target="_blank"
              rel="noopener noreferrer"
              class="block rounded-2xl bg-sky-600 px-5 py-3 text-center text-sm font-bold text-white transition hover:bg-sky-500"
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
        <h3 class="mt-4 text-xl font-black text-white">{{ confirmTitle }}</h3>
        <p class="mt-2 text-sm leading-6 text-slate-400">
          После подтверждения статус будет обновлён и станет виден второй стороне.
        </p>
        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            class="rounded-2xl bg-sky-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-sky-500 disabled:opacity-60"
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
