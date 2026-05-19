<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import api from '../api'
import { useAuthStore } from '../stores/auth'
import { showError, showSuccess } from '../utils/toast'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const pageError = ref('')
const activeTab = ref(authStore.isEmployer ? 'employer-vacancies' : 'vacancies')
const searchQuery = ref('')
const skillQuery = ref('')
const workFormat = ref('')
const employmentType = ref('')
const onlyMatched = ref(Boolean(authStore.isStudent))
const page = ref(1)
const pageSize = ref(9)
const totalVacancies = ref(0)

const vacancies = ref([])
const myApplications = ref([])
const employerVacancies = ref([])
const employerApplications = ref([])
const offers = ref([])

const applyModalOpen = ref(false)
const selectedVacancy = ref(null)
const applyMessage = ref('')
const submittingApply = ref(false)

const vacancyModalOpen = ref(false)
const editingVacancy = ref(null)
const savingVacancy = ref(false)

const applicationFilter = ref('all')
const employerLocalPage = ref(1)
const employerApplicationPage = ref(1)
const localPageSize = ref(6)
const mobileFiltersOpen = ref(false)

const vacancyForm = reactive({
  title: '',
  company_name: '',
  description: '',
  requirements: '',
  skill_names_text: '',
  work_format: 'any',
  employment_type: 'full_time',
  location: '',
  salary_from: '',
  salary_to: '',
  contact_link: '',
  status: 'published',
})

const tabs = computed(() => {
  if (authStore.isEmployer) {
    return [
      { id: 'employer-vacancies', label: 'Мои вакансии' },
      { id: 'applications', label: 'Отклики' },
      { id: 'sent-offers', label: 'Предложения' },
    ]
  }

  if (authStore.isStudent) {
    return [
      { id: 'vacancies', label: onlyMatched.value ? 'Подходящие' : 'Все вакансии' },
      { id: 'my-applications', label: 'Мои отклики' },
      { id: 'student-offers', label: 'Предложения мне' },
    ]
  }

  return [{ id: 'vacancies', label: 'Открытые вакансии' }]
})

const pageCount = computed(() => Math.max(1, Math.ceil(totalVacancies.value / pageSize.value)))
const hasFilters = computed(() => Boolean(searchQuery.value || skillQuery.value || workFormat.value || employmentType.value || onlyMatched.value))

const statusMeta = {
  draft: { label: 'Черновик', className: 'border-slate-600 bg-slate-800 text-slate-300' },
  published: { label: 'Опубликована', className: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200' },
  closed: { label: 'Закрыта', className: 'border-rose-400/30 bg-rose-500/10 text-rose-200' },
  pending: { label: 'Отправлен', className: 'border-sky-400/30 bg-sky-500/10 text-sky-200' },
  viewed: { label: 'Просмотрен', className: 'border-indigo-400/30 bg-indigo-500/10 text-indigo-200' },
  accepted: { label: 'Принят', className: 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200' },
  rejected: { label: 'Отклонён', className: 'border-rose-400/30 bg-rose-500/10 text-rose-200' },
  withdrawn: { label: 'Отозван', className: 'border-slate-600 bg-slate-800 text-slate-300' },
}

const workFormatLabels = {
  any: 'Любой формат',
  remote: 'Удалённо',
  office: 'В офисе',
  hybrid: 'Гибрид',
}

const employmentTypeLabels = {
  full_time: 'Полная занятость',
  part_time: 'Частичная занятость',
  internship: 'Стажировка',
  project: 'Проект',
}

const applicationStatusLabels = {
  pending: 'Ожидает ответа',
  viewed: 'Просмотрен',
  accepted: 'Принят',
  rejected: 'Отклонён',
  withdrawn: 'Отозван',
}

const formatSalary = (vacancy) => {
  const from = Number(vacancy?.salary_from || 0)
  const to = Number(vacancy?.salary_to || 0)
  if (from && to) return `${from.toLocaleString('ru-RU')} – ${to.toLocaleString('ru-RU')}`
  if (from) return `от ${from.toLocaleString('ru-RU')}`
  if (to) return `до ${to.toLocaleString('ru-RU')}`
  return 'по договорённости'
}

const formatDate = (value) => {
  if (!value) return 'нет данных'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'нет данных'
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

const statusClass = (status) => statusMeta[status]?.className || statusMeta.pending.className
const statusLabel = (status) => statusMeta[status]?.label || applicationStatusLabels[status] || status || 'Статус'

const briefText = (value, length = 180) => {
  const text = String(value || '').trim()
  if (text.length <= length) return text
  return `${text.slice(0, length).trim()}...`
}

const resetVacancyForm = () => {
  editingVacancy.value = null
  Object.assign(vacancyForm, {
    title: '',
    company_name: authStore.user?.username || '',
    description: '',
    requirements: '',
    skill_names_text: '',
    work_format: 'any',
    employment_type: 'full_time',
    location: '',
    salary_from: '',
    salary_to: '',
    contact_link: '',
    status: 'published',
  })
}

const parseSkillNames = (value) => String(value || '')
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean)
  .slice(0, 12)

const validateVacancyForm = () => {
  if (vacancyForm.title.trim().length < 3) return 'Название вакансии должно содержать минимум 3 символа.'
  if (vacancyForm.description.trim().length < 20) return 'Описание должно содержать минимум 20 символов.'
  if (vacancyForm.title.length > 160) return 'Название вакансии слишком длинное.'
  if (vacancyForm.description.length > 4000) return 'Описание не должно превышать 4000 символов.'
  if (vacancyForm.requirements.length > 3000) return 'Требования не должны превышать 3000 символов.'
  if (vacancyForm.contact_link && /javascript:|<|>/i.test(vacancyForm.contact_link)) return 'Контактная ссылка содержит недопустимые символы.'

  const salaryFrom = Number(vacancyForm.salary_from || 0)
  const salaryTo = Number(vacancyForm.salary_to || 0)
  if (salaryFrom && salaryTo && salaryFrom > salaryTo) return 'Зарплата “от” не может быть больше значения “до”.'
  return ''
}

const buildVacancyPayload = () => ({
  title: vacancyForm.title.trim(),
  company_name: vacancyForm.company_name.trim(),
  description: vacancyForm.description.trim(),
  requirements: vacancyForm.requirements.trim(),
  skill_names: parseSkillNames(vacancyForm.skill_names_text),
  work_format: vacancyForm.work_format,
  employment_type: vacancyForm.employment_type,
  location: vacancyForm.location.trim(),
  salary_from: vacancyForm.salary_from ? Number(vacancyForm.salary_from) : null,
  salary_to: vacancyForm.salary_to ? Number(vacancyForm.salary_to) : null,
  contact_link: vacancyForm.contact_link.trim(),
  status: vacancyForm.status,
})

const loadVacancies = async () => {
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/vacancies/', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value || undefined,
        skills: skillQuery.value || undefined,
        work_format: workFormat.value || undefined,
        employment_type: employmentType.value || undefined,
        matched: authStore.isStudent && onlyMatched.value ? '1' : undefined,
      },
    })

    const payload = response.data
    vacancies.value = Array.isArray(payload?.results) ? payload.results : Array.isArray(payload) ? payload : []
    totalVacancies.value = Number(payload?.count ?? vacancies.value.length)
  } catch (error) {
    console.error('Ошибка загрузки вакансий:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить вакансии.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const loadMyApplications = async () => {
  if (!authStore.isStudent) return
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/student/vacancy-applications/')
    myApplications.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки откликов:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить ваши отклики.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const loadStudentOffers = async () => {
  if (!authStore.isStudent) return
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/student/offers/')
    offers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки предложений:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить предложения.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const loadEmployerVacancies = async () => {
  if (!authStore.isEmployer) return
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/employer/vacancies/')
    employerVacancies.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки вакансий работодателя:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить вакансии работодателя.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const loadEmployerApplications = async () => {
  if (!authStore.isEmployer) return
  loading.value = true
  pageError.value = ''

  try {
    const params = {}
    if (applicationFilter.value !== 'all') params.status = applicationFilter.value
    const response = await api.get('/employer/vacancy-applications/', { params })
    employerApplications.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки откликов:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить отклики студентов.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const loadEmployerOffers = async () => {
  if (!authStore.isEmployer) return
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/employer/offers/')
    offers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('Ошибка загрузки предложений:', error)
    pageError.value = error?.response?.data?.detail || 'Не удалось загрузить отправленные предложения.'
    showError(pageError.value)
  } finally {
    loading.value = false
  }
}

const refreshCurrentTab = async () => {
  if (activeTab.value === 'vacancies') return loadVacancies()
  if (activeTab.value === 'my-applications') return loadMyApplications()
  if (activeTab.value === 'student-offers') return loadStudentOffers()
  if (activeTab.value === 'employer-vacancies') return loadEmployerVacancies()
  if (activeTab.value === 'applications') return loadEmployerApplications()
  if (activeTab.value === 'sent-offers') return loadEmployerOffers()
}

const setTab = (tab) => {
  activeTab.value = tab
  pageError.value = ''
  if (tab === 'vacancies') {
    page.value = 1
  }
  refreshCurrentTab()
}

const clearFilters = () => {
  searchQuery.value = ''
  skillQuery.value = ''
  workFormat.value = ''
  employmentType.value = ''
  onlyMatched.value = Boolean(authStore.isStudent)
  page.value = 1
  mobileFiltersOpen.value = false
  loadVacancies()
}

let filterTimer = null
watch([searchQuery, skillQuery, workFormat, employmentType, onlyMatched, pageSize], () => {
  if (activeTab.value !== 'vacancies') return
  page.value = 1
  window.clearTimeout(filterTimer)
  filterTimer = window.setTimeout(() => loadVacancies(), 350)
})

watch(page, () => {
  if (activeTab.value === 'vacancies') loadVacancies()
})

watch(applicationFilter, () => {
  if (activeTab.value === 'applications') {
    employerApplicationPage.value = 1
    loadEmployerApplications()
  }
})

const openApplyModal = (vacancy) => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }
  if (!authStore.isStudent) {
    showError('Откликаться на вакансии могут только студенты.')
    return
  }
  selectedVacancy.value = vacancy
  applyMessage.value = ''
  applyModalOpen.value = true
}

const submitApply = async () => {
  if (!selectedVacancy.value) return
  if (applyMessage.value.length > 1200) {
    showError('Сообщение не должно превышать 1200 символов.')
    return
  }

  submittingApply.value = true
  try {
    const response = await api.post(`/vacancies/${selectedVacancy.value.id}/apply/`, {
      message: applyMessage.value.trim(),
    })

    const application = response.data
    vacancies.value = vacancies.value.map((item) => item.id === selectedVacancy.value.id
      ? { ...item, application_id: application.id, application_status: application.status }
      : item)
    applyModalOpen.value = false
    showSuccess('Отклик отправлен работодателю.')
  } catch (error) {
    const message = error?.response?.data?.detail || error?.response?.data?.message?.[0] || 'Не удалось отправить отклик.'
    showError(message)
  } finally {
    submittingApply.value = false
  }
}

const openCreateVacancy = () => {
  resetVacancyForm()
  vacancyModalOpen.value = true
}

const openEditVacancy = (vacancy) => {
  editingVacancy.value = vacancy
  Object.assign(vacancyForm, {
    title: vacancy.title || '',
    company_name: vacancy.company_name || authStore.user?.username || '',
    description: vacancy.description || '',
    requirements: vacancy.requirements || '',
    skill_names_text: (vacancy.skills || []).map((skill) => skill.name).join(', '),
    work_format: vacancy.work_format || 'any',
    employment_type: vacancy.employment_type || 'full_time',
    location: vacancy.location || '',
    salary_from: vacancy.salary_from || '',
    salary_to: vacancy.salary_to || '',
    contact_link: vacancy.contact_link || '',
    status: vacancy.status || 'published',
  })
  vacancyModalOpen.value = true
}

const submitVacancy = async () => {
  const error = validateVacancyForm()
  if (error) {
    showError(error)
    return
  }

  savingVacancy.value = true
  try {
    const payload = buildVacancyPayload()
    if (editingVacancy.value) {
      await api.patch(`/employer/vacancies/${editingVacancy.value.id}/`, payload)
      showSuccess('Вакансия обновлена.')
    } else {
      await api.post('/employer/vacancies/', payload)
      showSuccess('Вакансия создана.')
    }
    vacancyModalOpen.value = false
    await loadEmployerVacancies()
  } catch (requestError) {
    const data = requestError?.response?.data || {}
    const firstField = Object.keys(data)[0]
    const message = data.detail || (firstField ? `${firstField}: ${Array.isArray(data[firstField]) ? data[firstField][0] : data[firstField]}` : 'Не удалось сохранить вакансию.')
    showError(message)
  } finally {
    savingVacancy.value = false
  }
}

const closeVacancy = async (vacancy) => {
  if (!window.confirm(`Закрыть вакансию “${vacancy.title}”?`)) return
  try {
    await api.delete(`/employer/vacancies/${vacancy.id}/`)
    showSuccess('Вакансия закрыта.')
    await loadEmployerVacancies()
  } catch (error) {
    showError(error?.response?.data?.detail || 'Не удалось закрыть вакансию.')
  }
}

const changeApplicationStatus = async (application, status) => {
  try {
    const response = await api.patch(`/employer/vacancy-applications/${application.id}/`, { status })
    employerApplications.value = employerApplications.value.map((item) => item.id === application.id ? response.data : item)
    showSuccess('Статус отклика обновлён.')
  } catch (error) {
    showError(error?.response?.data?.detail || 'Не удалось обновить статус отклика.')
  }
}

const paginatedEmployerVacancies = computed(() => {
  const start = (employerLocalPage.value - 1) * localPageSize.value
  return employerVacancies.value.slice(start, start + localPageSize.value)
})

const employerVacancyPages = computed(() => Math.max(1, Math.ceil(employerVacancies.value.length / localPageSize.value)))

const paginatedEmployerApplications = computed(() => {
  const start = (employerApplicationPage.value - 1) * localPageSize.value
  return employerApplications.value.slice(start, start + localPageSize.value)
})

const employerApplicationPages = computed(() => Math.max(1, Math.ceil(employerApplications.value.length / localPageSize.value)))

const stats = computed(() => {
  if (authStore.isEmployer) {
    const published = employerVacancies.value.filter((item) => item.status === 'published').length
    const applications = employerApplications.value.length
    return [
      { label: 'Вакансии', value: employerVacancies.value.length, caption: 'Всего создано' },
      { label: 'Опубликовано', value: published, caption: 'Доступны студентам' },
      { label: 'Отклики', value: applications, caption: 'От студентов' },
    ]
  }

  return [
    { label: 'Найдено', value: totalVacancies.value, caption: 'Открытые вакансии' },
    { label: 'Отклики', value: myApplications.value.length, caption: 'Ваши заявки' },
    { label: 'Предложения', value: offers.value.length, caption: 'От работодателей' },
  ]
})

onMounted(async () => {
  if (authStore.isStudent) {
    await Promise.allSettled([loadVacancies(), loadMyApplications(), loadStudentOffers()])
    return
  }

  if (authStore.isEmployer) {
    await Promise.allSettled([loadEmployerVacancies(), loadEmployerApplications(), loadEmployerOffers()])
    return
  }

  await loadVacancies()
})
</script>

<template>
  <div class="w-full pb-14">
    <header class="card-glass mb-4 overflow-hidden rounded-[1.6rem] sm:mb-5 sm:rounded-[2rem]">
      <div class="relative p-3.5 sm:p-6 lg:p-7">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/60 to-transparent"></div>
        <div class="flex flex-col gap-3.5 lg:flex-row lg:items-end lg:justify-between">
          <div class="min-w-0 max-w-3xl">
            <div class="mb-2 inline-flex items-center rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-sky-200 sm:mb-3 sm:px-3 sm:text-xs">
              Карьерный контур
            </div>
            <h1 class="break-words text-xl font-black tracking-tight text-slate-50 sm:text-3xl lg:text-4xl">Вакансии и отклики</h1>
            <p class="mt-2 max-w-2xl text-sm leading-5 text-slate-400 line-clamp-3 sm:mt-3 sm:leading-6 sm:line-clamp-none">
              Один раздел для поиска вакансий, откликов студентов и управления публикациями работодателя. Студентам по умолчанию показываются предложения по подтверждённым навыкам.
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2 self-start lg:self-auto">
            <button
              v-if="authStore.isEmployer"
              class="btn-primary inline-flex min-h-[38px] items-center justify-center px-4 text-center text-sm font-black"
              type="button"
              @click="openCreateVacancy"
            >
              Создать вакансию
            </button>
            <button
              class="btn-secondary inline-flex min-h-[38px] items-center justify-center gap-2 px-3.5 text-center text-sm font-semibold"
              type="button"
              @click="refreshCurrentTab"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m14.836 2A8.001 8.001 0 0 0 5.582 9m0 0H9m11 11v-5h-.581m0 0A8.003 8.003 0 0 1 4.582 15m14.837 0H15" />
              </svg>
              Обновить
            </button>
          </div>
        </div>
      </div>
    </header>

    <section class="mb-4 flex gap-2 overflow-x-auto pb-1 md:mb-5 md:grid md:grid-cols-3 md:overflow-visible">
      <article
        v-for="item in stats"
        :key="item.label"
        class="min-w-[112px] shrink-0 rounded-2xl border border-slate-800 bg-slate-900/55 px-3 py-2.5 md:min-w-0 md:px-4 md:py-4"
      >
        <p class="text-[11px] font-semibold text-slate-500 md:text-xs">{{ item.label }}</p>
        <div class="mt-1 flex items-baseline gap-2">
          <strong class="text-lg font-black text-slate-50 md:text-2xl">{{ item.value }}</strong>
          <span class="text-[11px] text-slate-500 line-clamp-1 md:text-xs">{{ item.caption }}</span>
        </div>
      </article>
    </section>

    <nav class="mb-4 overflow-x-auto rounded-3xl border border-slate-800 bg-slate-900/50 p-1.5 md:mb-5">
      <div class="flex min-w-max gap-1.5">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="rounded-full px-3.5 py-2 text-sm font-semibold transition whitespace-nowrap"
          :class="activeTab === tab.id ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'"
          type="button"
          @click="setTab(tab.id)"
        >
          {{ tab.label }}
        </button>
      </div>
    </nav>

    <section v-if="activeTab === 'vacancies'" class="grid gap-4 lg:grid-cols-[272px_minmax(0,1fr)]">
      <aside class="card-glass h-fit rounded-[1.4rem] p-3.5 sm:p-4">
        <div class="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-base font-bold text-slate-50">Фильтры</h2>
            <p class="mt-1 text-xs text-slate-500 sm:text-sm">Поиск по названию, навыкам и формату.</p>
          </div>
          <button
            class="btn-secondary inline-flex min-h-[36px] items-center gap-2 px-3 py-1.5 text-xs font-semibold lg:hidden"
            type="button"
            @click="mobileFiltersOpen = !mobileFiltersOpen"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h18M6 12h12m-7 8h2" />
            </svg>
            {{ mobileFiltersOpen ? 'Скрыть' : 'Показать' }}
          </button>
        </div>

        <div class="grid gap-3">
          <label class="grid gap-1.5 text-sm font-semibold text-slate-300">
            Поиск
            <input v-model="searchQuery" class="input-control min-h-[42px] py-2.5" type="search" placeholder="Frontend, Python, стажировка">
          </label>

          <div :class="mobileFiltersOpen ? 'grid gap-3' : 'hidden lg:grid lg:gap-3'">
            <label class="grid gap-1.5 text-sm font-semibold text-slate-300">
              Навыки
              <input v-model="skillQuery" class="input-control min-h-[42px] py-2.5" type="search" placeholder="Python, Vue, SQL">
            </label>

            <label class="grid gap-1.5 text-sm font-semibold text-slate-300">
              Формат
              <select v-model="workFormat" class="input-control min-h-[42px] py-2.5">
                <option value="">Любой</option>
                <option value="remote">Удалённо</option>
                <option value="office">В офисе</option>
                <option value="hybrid">Гибрид</option>
                <option value="any">Любой формат</option>
              </select>
            </label>

            <label class="grid gap-1.5 text-sm font-semibold text-slate-300">
              Занятость
              <select v-model="employmentType" class="input-control min-h-[42px] py-2.5">
                <option value="">Любая</option>
                <option value="full_time">Полная занятость</option>
                <option value="part_time">Частичная занятость</option>
                <option value="internship">Стажировка</option>
                <option value="project">Проект</option>
              </select>
            </label>

            <label v-if="authStore.isStudent" class="flex items-start gap-2.5 rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-300">
              <input v-model="onlyMatched" class="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-900 accent-sky-500" type="checkbox">
              <span>
                <strong class="block text-sm font-semibold text-slate-100">Только подходящие мне</strong>
                <span class="mt-0.5 block text-xs leading-5 text-slate-500">Фильтр использует навыки из вашего профиля.</span>
              </span>
            </label>

            <div class="grid gap-3 sm:grid-cols-[minmax(0,1fr),auto] sm:items-end">
              <label class="grid gap-1.5 text-sm font-semibold text-slate-300">
                На странице
                <select v-model.number="pageSize" class="input-control min-h-[42px] py-2.5">
                  <option :value="6">6</option>
                  <option :value="9">9</option>
                  <option :value="12">12</option>
                </select>
              </label>

              <button v-if="hasFilters" class="btn-secondary min-h-[42px] px-4 text-sm font-semibold" type="button" @click="clearFilters">
                Сбросить
              </button>
            </div>
          </div>
        </div>
      </aside>

      <div class="min-w-0">
        <div v-if="loading" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div v-for="index in pageSize" :key="index" class="h-60 animate-pulse rounded-[1.4rem] border border-slate-800 bg-slate-900/60"></div>
        </div>

        <div v-else-if="pageError" class="rounded-[2rem] border border-rose-500/30 bg-rose-500/10 p-8 text-center">
          <h2 class="text-xl font-black text-rose-100">Не удалось загрузить вакансии</h2>
          <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-rose-100/80">{{ pageError }}</p>
          <button class="btn-danger mt-6" type="button" @click="loadVacancies">Повторить</button>
        </div>

        <div v-else-if="vacancies.length" class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <article v-for="vacancy in vacancies" :key="vacancy.id" class="flex min-h-[252px] flex-col rounded-[1.4rem] border border-slate-800 bg-slate-900/60 p-4 transition hover:border-sky-400/40 hover:bg-slate-900/85">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
               <div class="min-w-0">
                <p class="text-[11px] font-semibold text-slate-500">{{ vacancy.company_name || vacancy.employer_name }}</p>
                <h3 class="mt-1 line-clamp-2 text-lg font-black text-slate-50">{{ vacancy.title }}</h3>
              </div>
              <span class="shrink-0 rounded-full border px-2.5 py-1 text-xs font-bold" :class="statusClass(vacancy.status)">{{ statusLabel(vacancy.status) }}</span>
            </div>

            <p class="mt-3 line-clamp-4 flex-1 text-sm leading-6 text-slate-400">{{ briefText(vacancy.description, 210) }}</p>

            <div class="mt-3 flex flex-wrap gap-1.5">
              <span v-for="skill in (vacancy.skills || []).slice(0, 5)" :key="skill.id" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-[11px] font-semibold text-sky-200">
                {{ skill.name }}
              </span>
              <span v-if="vacancy.match_count" class="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-200">
                Совпадений: {{ vacancy.match_count }}
              </span>
            </div>

            <div class="mt-3 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
              <div class="rounded-xl border border-slate-800 bg-slate-950/30 px-3 py-2">
                <span class="block text-slate-500">Формат</span>
                <strong class="mt-1 block text-xs font-semibold text-slate-200">{{ workFormatLabels[vacancy.work_format] || vacancy.work_format }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-950/30 px-3 py-2">
                <span class="block text-slate-500">Занятость</span>
                <strong class="mt-1 block text-xs font-semibold text-slate-200">{{ employmentTypeLabels[vacancy.employment_type] || vacancy.employment_type }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-950/30 px-3 py-2">
                <span class="block text-slate-500">Локация</span>
                <strong class="mt-1 block truncate text-xs font-semibold text-slate-200">{{ vacancy.location || 'не указана' }}</strong>
              </div>
              <div class="rounded-xl border border-slate-800 bg-slate-950/30 px-3 py-2">
                <span class="block text-slate-500">Оплата</span>
                <strong class="mt-1 block truncate text-xs font-semibold text-slate-200">{{ formatSalary(vacancy) }}</strong>
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <button v-if="vacancy.application_status" class="rounded-full border border-slate-700 bg-slate-800/70 px-4 py-2 text-sm font-semibold text-slate-300" type="button" disabled>
                Отклик: {{ statusLabel(vacancy.application_status) }}
              </button>
              <button v-else class="btn-primary px-4 py-2 text-sm font-semibold" type="button" @click="openApplyModal(vacancy)">
                {{ authStore.isAuthenticated ? 'Откликнуться' : 'Войти, чтобы откликнуться' }}
              </button>
            </div>
          </article>
        </div>

        <div v-else class="rounded-[2rem] border border-dashed border-slate-700 p-10 text-center">
          <h2 class="text-xl font-black text-slate-100">Вакансии не найдены</h2>
          <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">Измените фильтры или отключите режим подходящих вакансий.</p>
          <button v-if="hasFilters" class="btn-secondary mt-6" type="button" @click="clearFilters">Показать все вакансии</button>
        </div>

        <div v-if="pageCount > 1" class="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-slate-800 bg-slate-900/50 p-3">
          <p class="text-sm text-slate-500">Страница {{ page }} из {{ pageCount }}</p>
          <div class="flex flex-wrap gap-2">
            <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" type="button" :disabled="page <= 1" @click="page -= 1">Назад</button>
            <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" type="button" :disabled="page >= pageCount" @click="page += 1">Вперёд</button>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="activeTab === 'my-applications'" class="rounded-[1.6rem] border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <h2 class="text-xl font-black text-slate-50">Мои отклики</h2>
      <p class="mt-1 text-sm text-slate-500">История ваших откликов на вакансии.</p>

      <div v-if="loading" class="mt-5 grid gap-3">
        <div v-for="index in 4" :key="index" class="h-28 animate-pulse rounded-3xl border border-slate-800 bg-slate-950/40"></div>
      </div>

      <div v-else-if="myApplications.length" class="mt-4 grid gap-3">
        <article v-for="application in myApplications" :key="application.id" class="rounded-[1.35rem] border border-slate-800 bg-slate-950/30 p-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 class="text-lg font-black text-slate-50">{{ application.vacancy?.title || 'Вакансия' }}</h3>
              <p class="mt-1 text-sm text-slate-500">{{ application.vacancy?.company_name || application.vacancy?.employer_name }} · {{ formatDate(application.created_at) }}</p>
            </div>
            <span class="w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="statusClass(application.status)">{{ statusLabel(application.status) }}</span>
          </div>
          <p v-if="application.message" class="mt-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-sm leading-6 text-slate-400">{{ application.message }}</p>
        </article>
      </div>

      <div v-else class="mt-4 rounded-[1.35rem] border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
        Пока нет откликов. Откройте вкладку вакансий и отправьте первый отклик.
      </div>
    </section>

    <section v-else-if="activeTab === 'student-offers'" class="rounded-[1.6rem] border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <h2 class="text-xl font-black text-slate-50">Предложения мне</h2>
      <p class="mt-1 text-sm text-slate-500">Прямые предложения работодателей из существующего карьерного контура.</p>

      <div v-if="offers.length" class="mt-4 grid gap-3">
        <article v-for="offer in offers" :key="offer.id" class="rounded-[1.35rem] border border-slate-800 bg-slate-950/30 p-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 class="text-lg font-black text-slate-50">{{ offer.employer_name || 'Работодатель' }}</h3>
              <p class="mt-1 text-sm text-slate-500">{{ formatDate(offer.created_at) }}</p>
            </div>
            <span class="w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="statusClass(offer.status)">{{ statusLabel(offer.status) }}</span>
          </div>
          <p class="mt-3 line-clamp-4 text-sm leading-6 text-slate-400">{{ offer.message || 'Сообщение не указано.' }}</p>
          <a v-if="offer.contact_link" :href="offer.contact_link" target="_blank" rel="noreferrer" class="mt-3 inline-flex rounded-full border border-sky-400/30 px-4 py-2 text-sm font-semibold text-sky-200 transition hover:bg-sky-500 hover:text-white">Открыть контакт</a>
        </article>
      </div>

      <div v-else class="mt-4 rounded-[1.35rem] border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
        Предложений пока нет.
      </div>
    </section>

    <section v-else-if="activeTab === 'employer-vacancies'" class="rounded-[1.6rem] border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <div class="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-50">Мои вакансии</h2>
          <p class="mt-1 text-sm text-slate-500">Создавайте публикации и отслеживайте отклики студентов.</p>
        </div>
        <button class="btn-primary min-h-[38px] px-4 text-sm font-semibold" type="button" @click="openCreateVacancy">Создать вакансию</button>
      </div>

      <div v-if="loading" class="grid gap-4 md:grid-cols-2">
        <div v-for="index in 4" :key="index" class="h-56 animate-pulse rounded-3xl border border-slate-800 bg-slate-950/40"></div>
      </div>

      <div v-else-if="paginatedEmployerVacancies.length" class="grid gap-3 lg:grid-cols-2">
        <article v-for="vacancy in paginatedEmployerVacancies" :key="vacancy.id" class="rounded-[1.35rem] border border-slate-800 bg-slate-950/30 p-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h3 class="text-lg font-black text-slate-50">{{ vacancy.title }}</h3>
              <p class="mt-1 text-sm text-slate-500">{{ formatDate(vacancy.created_at) }} · откликов: {{ vacancy.applications_count || 0 }}</p>
            </div>
            <span class="rounded-full border px-3 py-1 text-xs font-bold" :class="statusClass(vacancy.status)">{{ statusLabel(vacancy.status) }}</span>
          </div>

          <p class="mt-3 line-clamp-4 text-sm leading-6 text-slate-400">{{ briefText(vacancy.description, 220) }}</p>

          <div class="mt-4 flex flex-wrap gap-2">
            <span v-for="skill in (vacancy.skills || []).slice(0, 6)" :key="skill.id" class="rounded-full border border-sky-400/20 bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-200">{{ skill.name }}</span>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <button class="btn-primary px-4 py-2 text-sm font-semibold" type="button" @click="openEditVacancy(vacancy)">Редактировать</button>
            <button class="btn-secondary px-4 py-2 text-sm font-semibold hover:border-rose-400 hover:text-rose-200" type="button" @click="closeVacancy(vacancy)">Закрыть</button>
          </div>
        </article>
      </div>

      <div v-else class="rounded-[1.35rem] border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
        У вас пока нет вакансий. Создайте первую вакансию, чтобы студенты могли откликнуться.
      </div>

      <div v-if="employerVacancyPages > 1" class="mt-5 flex flex-wrap justify-end gap-2">
        <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" :disabled="employerLocalPage <= 1" @click="employerLocalPage -= 1">Назад</button>
        <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" :disabled="employerLocalPage >= employerVacancyPages" @click="employerLocalPage += 1">Вперёд</button>
      </div>
    </section>

    <section v-else-if="activeTab === 'applications'" class="rounded-[1.6rem] border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <div class="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-50">Отклики студентов</h2>
          <p class="mt-1 text-sm text-slate-500">Просматривайте заявки и обновляйте статус.</p>
        </div>
        <select v-model="applicationFilter" class="w-full rounded-full border border-slate-700 bg-slate-950/60 px-4 py-2.5 text-sm font-semibold text-slate-100 outline-none focus:border-sky-400 md:w-auto">
          <option value="all">Все статусы</option>
          <option value="pending">Отправленные</option>
          <option value="viewed">Просмотренные</option>
          <option value="accepted">Принятые</option>
          <option value="rejected">Отклонённые</option>
        </select>
      </div>

      <div v-if="paginatedEmployerApplications.length" class="grid gap-3">
        <article v-for="application in paginatedEmployerApplications" :key="application.id" class="rounded-[1.35rem] border border-slate-800 bg-slate-950/30 p-4">
          <div class="grid gap-4 lg:grid-cols-[1fr_1.2fr_auto] lg:items-center">
            <div>
              <h3 class="font-black text-slate-50">{{ application.student_username }}</h3>
              <p class="mt-1 text-sm text-slate-500">{{ application.student_email || 'email не указан' }}</p>
            </div>
            <div>
              <p class="font-bold text-slate-200">{{ application.vacancy?.title || 'Вакансия' }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ formatDate(application.created_at) }}</p>
            </div>
            <span class="w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="statusClass(application.status)">{{ statusLabel(application.status) }}</span>
          </div>

          <p v-if="application.message" class="mt-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-sm leading-6 text-slate-400">{{ application.message }}</p>

          <div class="mt-3 flex flex-wrap gap-2">
            <button class="rounded-full border border-indigo-400/30 px-4 py-2 text-sm font-semibold text-indigo-200 transition hover:bg-indigo-500 hover:text-white" type="button" @click="changeApplicationStatus(application, 'viewed')">Просмотрен</button>
            <button class="rounded-full border border-emerald-400/30 px-4 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500 hover:text-white" type="button" @click="changeApplicationStatus(application, 'accepted')">Принять</button>
            <button class="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-semibold text-rose-200 transition hover:bg-rose-500 hover:text-white" type="button" @click="changeApplicationStatus(application, 'rejected')">Отклонить</button>
          </div>
        </article>
      </div>

      <div v-else class="rounded-[1.35rem] border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
        Откликов пока нет.
      </div>

      <div v-if="employerApplicationPages > 1" class="mt-5 flex flex-wrap justify-end gap-2">
        <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" :disabled="employerApplicationPage <= 1" @click="employerApplicationPage -= 1">Назад</button>
        <button class="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-300 disabled:opacity-40" :disabled="employerApplicationPage >= employerApplicationPages" @click="employerApplicationPage += 1">Вперёд</button>
      </div>
    </section>

    <section v-else-if="activeTab === 'sent-offers'" class="rounded-[1.6rem] border border-slate-800 bg-slate-900/60 p-4 sm:p-5">
      <h2 class="text-xl font-black text-slate-50">Отправленные предложения</h2>
      <p class="mt-1 text-sm text-slate-500">Прямые офферы студентам из раздела кандидатов.</p>

      <div v-if="offers.length" class="mt-4 grid gap-3">
        <article v-for="offer in offers" :key="offer.id" class="rounded-[1.35rem] border border-slate-800 bg-slate-950/30 p-4">
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 class="text-lg font-black text-slate-50">{{ offer.student_name || 'Студент' }}</h3>
              <p class="mt-1 text-sm text-slate-500">{{ formatDate(offer.created_at) }}</p>
            </div>
            <span class="w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="statusClass(offer.status)">{{ statusLabel(offer.status) }}</span>
          </div>
          <p class="mt-3 line-clamp-4 text-sm leading-6 text-slate-400">{{ offer.message || 'Сообщение не указано.' }}</p>
        </article>
      </div>

      <div v-else class="mt-4 rounded-[1.35rem] border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
        Прямых предложений пока нет.
      </div>
    </section>

    <div v-if="applyModalOpen" class="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur sm:p-4">
      <div class="modal-panel max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[1.6rem] p-4 sm:p-5">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 class="text-2xl font-black text-slate-50">Отклик на вакансию</h2>
            <p class="mt-1 text-sm text-slate-500">{{ selectedVacancy?.title }}</p>
          </div>
          <button class="btn-secondary px-3 py-2 text-sm" type="button" @click="applyModalOpen = false">Закрыть</button>
        </div>

        <label class="mt-5 grid gap-2 text-sm font-bold text-slate-300">
          Сообщение работодателю
          <textarea v-model="applyMessage" class="input-control min-h-32 resize-y leading-6" maxlength="1200" placeholder="Коротко напишите, почему вам интересна вакансия..."></textarea>
          <span class="text-right text-xs text-slate-500">{{ applyMessage.length }}/1200</span>
        </label>

        <div class="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button class="btn-secondary" type="button" @click="applyModalOpen = false">Отмена</button>
          <button class="btn-primary text-sm font-black" type="button" :disabled="submittingApply" @click="submitApply">
            {{ submittingApply ? 'Отправка...' : 'Отправить отклик' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="vacancyModalOpen" class="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/80 p-3 backdrop-blur sm:p-4">
      <form class="modal-panel max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-[1.6rem] p-4 sm:p-5" @submit.prevent="submitVacancy">
        <div class="sticky top-0 z-10 -mx-4 -mt-4 mb-5 flex flex-col gap-3 border-b border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:-mt-6 sm:flex-row sm:items-start sm:justify-between sm:px-6 sm:py-5">
          <div>
            <h2 class="text-2xl font-black text-slate-50">{{ editingVacancy ? 'Редактирование вакансии' : 'Новая вакансия' }}</h2>
            <p class="mt-1 text-sm text-slate-500">Заполните данные, которые увидят студенты.</p>
          </div>
          <button class="btn-secondary px-3 py-2 text-sm" type="button" @click="vacancyModalOpen = false">Закрыть</button>
        </div>

        <div class="grid gap-4 lg:grid-cols-2">
          <label class="grid gap-2 text-sm font-bold text-slate-300 lg:col-span-2">
            Название вакансии
            <input v-model="vacancyForm.title" class="input-control" maxlength="160" placeholder="Например: Junior Python Developer">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Компания
            <input v-model="vacancyForm.company_name" class="input-control" maxlength="160" placeholder="Название компании">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Статус
            <select v-model="vacancyForm.status" class="input-control">
              <option value="published">Опубликована</option>
              <option value="draft">Черновик</option>
              <option value="closed">Закрыта</option>
            </select>
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300 lg:col-span-2">
            Описание
            <textarea v-model="vacancyForm.description" class="input-control min-h-32 resize-y leading-6" maxlength="4000" placeholder="Опишите задачи, стек и кого ищете..."></textarea>
            <span class="text-right text-xs text-slate-500">{{ vacancyForm.description.length }}/4000</span>
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300 lg:col-span-2">
            Требования
            <textarea v-model="vacancyForm.requirements" class="input-control min-h-28 resize-y leading-6" maxlength="3000" placeholder="Например: базовые знания Django, REST API, SQL..."></textarea>
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300 lg:col-span-2">
            Навыки через запятую
            <input v-model="vacancyForm.skill_names_text" class="input-control" placeholder="Python, Django, PostgreSQL">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Формат работы
            <select v-model="vacancyForm.work_format" class="input-control">
              <option value="any">Любой формат</option>
              <option value="remote">Удалённо</option>
              <option value="office">В офисе</option>
              <option value="hybrid">Гибрид</option>
            </select>
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Тип занятости
            <select v-model="vacancyForm.employment_type" class="input-control">
              <option value="full_time">Полная занятость</option>
              <option value="part_time">Частичная занятость</option>
              <option value="internship">Стажировка</option>
              <option value="project">Проект</option>
            </select>
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Локация
            <input v-model="vacancyForm.location" class="input-control" maxlength="160" placeholder="Бишкек / удалённо">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Контактная ссылка
            <input v-model="vacancyForm.contact_link" class="input-control" maxlength="255" placeholder="https://t.me/hr">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Зарплата от
            <input v-model="vacancyForm.salary_from" class="input-control" min="0" type="number" placeholder="50000">
          </label>

          <label class="grid gap-2 text-sm font-bold text-slate-300">
            Зарплата до
            <input v-model="vacancyForm.salary_to" class="input-control" min="0" type="number" placeholder="120000">
          </label>
        </div>

        <div class="sticky bottom-0 -mx-4 -mb-4 mt-6 flex flex-col-reverse gap-3 border-t border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:-mx-6 sm:-mb-6 sm:flex-row sm:justify-end sm:px-6 sm:py-5">
          <button class="btn-secondary" type="button" @click="vacancyModalOpen = false">Отмена</button>
          <button class="btn-primary text-sm font-black" type="submit" :disabled="savingVacancy">
            {{ savingVacancy ? 'Сохранение...' : 'Сохранить вакансию' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
