<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'

import api from '../api'
import { showError, showSuccess } from '../utils/toast'

const TITLE_LIMIT = 120
const DESCRIPTION_LIMIT = 2000
const IMAGE_LIMIT_MB = 5

const myCourses = ref([])
const availableSkills = ref([])
const loading = ref(true)
const pageError = ref('')

const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentCourseId = ref(null)
const currentImageUrl = ref('')
const selectedImageName = ref('')
const isSaving = ref(false)
const modalError = ref('')
const skillSearch = ref('')
const imageInputRef = ref(null)
const descriptionTextarea = ref(null)

const courseForm = reactive({
  title: '',
  description: '',
  image: null,
  skills_covered: [],
})

const confirmDialog = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  pending: false,
  action: null,
})

const normalizeList = (value) => (Array.isArray(value) ? value : [])

const getCourseSkills = (course) => normalizeList(course?.skills_covered)

const getSkillId = (skill) => (typeof skill === 'object' ? skill.id : skill)
const getSkillName = (skill) => (typeof skill === 'object' ? skill.name : String(skill))

const getLessonCount = (course) => {
  const direct = course?.lesson_count ?? course?.lessons_count
  if (Number.isFinite(Number(direct))) return Number(direct)

  const lessons = normalizeList(course?.lessons)
  if (lessons.length) return lessons.length

  const modules = normalizeList(course?.modules)
  if (modules.length) {
    return modules.reduce((sum, module) => sum + normalizeList(module?.lessons).length, 0)
  }

  return 0
}

const getModuleCount = (course) => {
  const direct = course?.module_count ?? course?.modules_count
  if (Number.isFinite(Number(direct))) return Number(direct)
  return normalizeList(course?.modules).length
}

const isCoursePublished = (course) => {
  if (typeof course?.is_published === 'boolean') return course.is_published
  if (course?.status) return ['published', 'active', 'public'].includes(String(course.status).toLowerCase())
  return true
}

const getCourseStatus = (course) => {
  if (isCoursePublished(course)) {
    return {
      label: 'Опубликован',
      className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    }
  }

  return {
    label: 'Черновик',
    className: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  }
}

const truncateText = (text, limit = 150) => {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  if (!value) return 'Описание курса пока не заполнено.'
  return value.length > limit ? `${value.slice(0, limit).trim()}...` : value
}

const formatDate = (value) => {
  if (!value) return 'дата не указана'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'дата не указана'
  return new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }).format(date)
}

const dashboardStats = computed(() => {
  const courses = myCourses.value
  const skillIds = new Set()

  courses.forEach((course) => {
    getCourseSkills(course).forEach((skill) => skillIds.add(getSkillId(skill)))
  })

  return {
    total: courses.length,
    published: courses.filter(isCoursePublished).length,
    modules: courses.reduce((sum, course) => sum + getModuleCount(course), 0),
    lessons: courses.reduce((sum, course) => sum + getLessonCount(course), 0),
    skills: skillIds.size,
  }
})

const sortedCourses = computed(() => {
  return [...myCourses.value].sort((a, b) => {
    const dateA = new Date(a?.updated_at || a?.created_at || 0).getTime()
    const dateB = new Date(b?.updated_at || b?.created_at || 0).getTime()
    return dateB - dateA
  })
})

const filteredSkills = computed(() => {
  const query = skillSearch.value.trim().toLowerCase()
  if (!query) return availableSkills.value
  return availableSkills.value.filter((skill) => String(skill.name || '').toLowerCase().includes(query))
})

const selectedSkillsPreview = computed(() => {
  const ids = new Set(courseForm.skills_covered)
  return availableSkills.value.filter((skill) => ids.has(skill.id))
})

const autoGrowElement = (element) => {
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 260)}px`
}

const autoGrowTextarea = (event) => {
  autoGrowElement(event.target)
}

const resetImageInput = () => {
  if (imageInputRef.value) {
    imageInputRef.value.value = ''
  }
}

const resetForm = () => {
  courseForm.title = ''
  courseForm.description = ''
  courseForm.image = null
  courseForm.skills_covered = []
  currentCourseId.value = null
  currentImageUrl.value = ''
  selectedImageName.value = ''
  modalError.value = ''
  skillSearch.value = ''
  resetImageInput()
}

const fetchMyCourses = async () => {
  loading.value = true
  pageError.value = ''

  try {
    const response = await api.get('/teacher/courses/')
    myCourses.value = Array.isArray(response.data) ? response.data : response.data?.results || []
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
    pageError.value = 'Не удалось загрузить курсы преподавателя.'
    showError('Не удалось загрузить курсы преподавателя.')
  } finally {
    loading.value = false
  }
}

const fetchSkills = async () => {
  try {
    const response = await api.get('/skills/')
    availableSkills.value = Array.isArray(response.data) ? response.data : response.data?.results || []
  } catch (error) {
    console.error('Ошибка загрузки навыков:', error)
  }
}

const openCreateModal = () => {
  isEditMode.value = false
  resetForm()
  isModalOpen.value = true
}

const openEditModal = (course) => {
  isEditMode.value = true
  resetForm()
  currentCourseId.value = course.id
  currentImageUrl.value = course.image || ''

  courseForm.title = course.title || ''
  courseForm.description = course.description || ''
  courseForm.skills_covered = getCourseSkills(course).map(getSkillId).filter(Boolean)

  isModalOpen.value = true
}

const closeCourseModal = () => {
  if (isSaving.value) return
  isModalOpen.value = false
}

const handleFileUpload = (event) => {
  const file = event.target.files?.[0]
  modalError.value = ''

  if (!file) {
    courseForm.image = null
    selectedImageName.value = ''
    return
  }

  if (!file.type.startsWith('image/')) {
    modalError.value = 'Можно загрузить только изображение обложки.'
    courseForm.image = null
    selectedImageName.value = ''
    resetImageInput()
    return
  }

  if (file.size > IMAGE_LIMIT_MB * 1024 * 1024) {
    modalError.value = `Размер обложки не должен превышать ${IMAGE_LIMIT_MB} МБ.`
    courseForm.image = null
    selectedImageName.value = ''
    resetImageInput()
    return
  }

  courseForm.image = file
  selectedImageName.value = file.name
}

const validateForm = () => {
  const title = courseForm.title.trim()
  const description = courseForm.description.trim()

  if (!title) return 'Введите название курса.'
  if (title.length > TITLE_LIMIT) return `Название курса не должно превышать ${TITLE_LIMIT} символов.`
  if (!description) return 'Введите описание курса.'
  if (description.length > DESCRIPTION_LIMIT) return `Описание курса не должно превышать ${DESCRIPTION_LIMIT} символов.`

  return ''
}

const saveCourse = async () => {
  modalError.value = validateForm()
  if (modalError.value || isSaving.value) return

  isSaving.value = true

  try {
    const formData = new FormData()
    formData.append('title', courseForm.title.trim())
    formData.append('description', courseForm.description.trim())

    if (courseForm.image) {
      formData.append('image', courseForm.image)
    }

    courseForm.skills_covered.forEach((skillId) => {
      formData.append('skills_covered', skillId)
    })

    if (isEditMode.value) {
      await api.patch(`/teacher/courses/${currentCourseId.value}/`, formData)
      showSuccess('Курс обновлен.')
    } else {
      await api.post('/teacher/courses/', formData)
      showSuccess('Курс создан.')
    }

    isModalOpen.value = false
    await fetchMyCourses()
  } catch (error) {
    console.error(error)
    const serverMessage = error?.response?.data?.detail || error?.response?.data?.title?.[0] || error?.response?.data?.description?.[0]
    modalError.value = serverMessage || 'Ошибка при сохранении курса.'
    showError(modalError.value)
  } finally {
    isSaving.value = false
  }
}

const openDeleteCourse = (course) => {
  confirmDialog.open = true
  confirmDialog.title = 'Удалить курс?'
  confirmDialog.message = `Курс «${course.title}» будет удалён вместе со структурой обучения, если это разрешено сервером. Это действие нельзя отменить.`
  confirmDialog.confirmText = 'Удалить курс'
  confirmDialog.action = async () => {
    await api.delete(`/teacher/courses/${course.id}/`)
    await fetchMyCourses()
    showSuccess('Курс удален.')
  }
}

const closeConfirmDialog = () => {
  if (confirmDialog.pending) return
  confirmDialog.open = false
  confirmDialog.action = null
}

const confirmAction = async () => {
  if (!confirmDialog.action || confirmDialog.pending) return
  confirmDialog.pending = true

  try {
    await confirmDialog.action()
    confirmDialog.open = false
    confirmDialog.action = null
  } catch (error) {
    console.error(error)
    showError('Не удалось выполнить действие.')
  } finally {
    confirmDialog.pending = false
  }
}

watch(isModalOpen, async (value) => {
  if (value) {
    await nextTick()
    autoGrowElement(descriptionTextarea.value)
  }
})

onMounted(async () => {
  await Promise.all([fetchMyCourses(), fetchSkills()])
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-0 py-6 sm:px-6 sm:py-8 lg:px-8">
    <header class="mb-8 overflow-hidden rounded-[2rem] border border-slate-700/60 bg-slate-900/70 shadow-2xl shadow-slate-950/20 backdrop-blur">
      <div class="relative p-4 sm:p-8">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-400/70 to-transparent"></div>
        <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="min-w-0 max-w-3xl">
            <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.24em] text-indigo-200">
              Панель преподавателя
            </div>
            <h1 class="break-words text-2xl font-black tracking-tight text-slate-50 sm:text-4xl">Управление курсами</h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
              Создавайте учебные программы, настраивайте структуру модулей, управляйте тестами и проверяйте внешний вид курса перед публикацией.
            </p>
          </div>

          <div class="grid gap-3 sm:flex sm:flex-wrap">
            <RouterLink
              :to="{ name: 'teacher-analytics' }"
              class="inline-flex items-center justify-center gap-2 rounded-2xl border border-sky-400/30 bg-sky-500/10 px-5 py-3 text-center text-sm font-black text-sky-100 transition hover:bg-sky-500 hover:text-white"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 19V5M5 19h14M9 15v-4M13 15V8M17 15v-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              Аналитика
            </RouterLink>

            <button
              class="inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-center text-sm font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 active:scale-[0.98]"
              type="button"
              @click="openCreateModal"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              Создать курс
            </button>
          </div>
        </div>
      </div>
    </header>

    <section class="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <article class="rounded-3xl border border-slate-700/60 bg-slate-900/55 p-5 shadow-lg shadow-slate-950/10">
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Курсы</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <strong class="text-3xl font-black text-slate-50">{{ dashboardStats.total }}</strong>
          <span class="rounded-2xl border border-slate-700 bg-slate-800/80 p-2 text-slate-300">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4H19v14.5A1.5 1.5 0 0 1 17.5 20H7a2 2 0 0 1-2-2V6.5Z" stroke="currentColor" stroke-width="1.8" />
              <path d="M8 8h7M8 11.5h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>
        </div>
      </article>

      <article class="rounded-3xl border border-slate-700/60 bg-slate-900/55 p-5 shadow-lg shadow-slate-950/10">
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Опубликовано</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <strong class="text-3xl font-black text-emerald-300">{{ dashboardStats.published }}</strong>
          <span class="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-2 text-emerald-300">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="m5 12 4 4L19 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
      </article>

      <article class="rounded-3xl border border-slate-700/60 bg-slate-900/55 p-5 shadow-lg shadow-slate-950/10">
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Модули</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <strong class="text-3xl font-black text-slate-50">{{ dashboardStats.modules }}</strong>
          <span class="rounded-2xl border border-sky-500/20 bg-sky-500/10 p-2 text-sky-300">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
          </span>
        </div>
      </article>

      <article class="rounded-3xl border border-slate-700/60 bg-slate-900/55 p-5 shadow-lg shadow-slate-950/10">
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Уроки</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <strong class="text-3xl font-black text-slate-50">{{ dashboardStats.lessons }}</strong>
          <span class="rounded-2xl border border-violet-500/20 bg-violet-500/10 p-2 text-violet-300">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M7 4h10a2 2 0 0 1 2 2v14l-7-3-7 3V6a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
      </article>

      <article class="rounded-3xl border border-slate-700/60 bg-slate-900/55 p-5 shadow-lg shadow-slate-950/10">
        <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Навыки</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <strong class="text-3xl font-black text-slate-50">{{ dashboardStats.skills }}</strong>
          <span class="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-2 text-amber-300">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 3 4 7l8 4 8-4-8-4Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
              <path d="m4 12 8 4 8-4M4 17l8 4 8-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
      </article>
    </section>

    <section class="rounded-[2rem] border border-slate-700/60 bg-slate-900/50 p-4 shadow-2xl shadow-slate-950/10 sm:p-6">
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-xl font-black text-slate-50">Мои курсы</h2>
          <p class="mt-1 text-sm text-slate-500">Рабочий список курсов преподавателя.</p>
        </div>
        <button
          class="inline-flex items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm font-bold text-slate-200 transition hover:border-indigo-400/60 hover:text-white"
          type="button"
          @click="fetchMyCourses"
        >
          Обновить
        </button>
      </div>

      <div v-if="loading" class="grid gap-4">
        <div v-for="index in 3" :key="index" class="animate-pulse rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <div class="flex gap-5">
            <div class="h-24 w-32 rounded-2xl bg-slate-800"></div>
            <div class="flex-1 space-y-3">
              <div class="h-5 w-2/3 rounded bg-slate-800"></div>
              <div class="h-4 w-full rounded bg-slate-800"></div>
              <div class="h-4 w-1/2 rounded bg-slate-800"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="pageError" class="rounded-3xl border border-rose-500/30 bg-rose-500/10 p-6 text-center">
        <h3 class="text-lg font-black text-rose-200">Не удалось загрузить данные</h3>
        <p class="mt-2 text-sm text-rose-100/80">{{ pageError }}</p>
        <button class="mt-5 rounded-2xl bg-rose-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-rose-400" type="button" @click="fetchMyCourses">
          Повторить
        </button>
      </div>

      <div v-else-if="!sortedCourses.length" class="rounded-3xl border border-dashed border-slate-700 bg-slate-950/30 p-8 text-center">
        <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 text-indigo-200">
          <svg class="h-7 w-7" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4H19v14.5A1.5 1.5 0 0 1 17.5 20H7a2 2 0 0 1-2-2V6.5Z" stroke="currentColor" stroke-width="1.8" />
            <path d="M8 8h7M8 11.5h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </div>
        <h3 class="mt-4 text-xl font-black text-slate-100">Курсы пока не созданы</h3>
        <p class="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
          Создайте первый курс, затем добавьте модули, уроки, HLS-видео, материалы и тестовые задания.
        </p>
        <button class="mt-6 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500" type="button" @click="openCreateModal">
          Создать первый курс
        </button>
      </div>

      <div v-else class="grid gap-5">
        <article
          v-for="course in sortedCourses"
          :key="course.id"
          class="group overflow-hidden rounded-3xl border border-slate-700/60 bg-slate-950/30 shadow-lg shadow-slate-950/10 transition hover:border-indigo-400/40 hover:bg-slate-900/70"
        >
          <div class="grid gap-5 p-4 md:grid-cols-[180px_minmax(0,1fr)] md:p-5">
            <div class="relative h-44 overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 md:h-full">
              <img v-if="course.image" :src="course.image" :alt="course.title" class="h-full w-full object-cover transition duration-500 group-hover:scale-105">
              <div v-else class="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-800 to-slate-950 text-slate-500">
                <svg class="h-9 w-9" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 16.5v-9Z" stroke="currentColor" stroke-width="1.8" />
                  <path d="m7 15 3-3 2 2 2-2 3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <span class="text-xs font-bold uppercase tracking-[0.2em]">Без обложки</span>
              </div>
              <span class="absolute left-3 top-3 rounded-full border px-3 py-1 text-xs font-black backdrop-blur" :class="getCourseStatus(course).className">
                {{ getCourseStatus(course).label }}
              </span>
            </div>

            <div class="min-w-0">
              <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div class="min-w-0">
                  <h3 class="line-clamp-2 text-2xl font-black leading-tight text-slate-50">{{ course.title }}</h3>
                  <p class="mt-2 text-sm leading-6 text-slate-400">{{ truncateText(course.description) }}</p>
                </div>

                <div class="flex shrink-0 flex-wrap gap-2 xl:justify-end">
                  <RouterLink
                    :to="{ name: 'teacher-lesson-editor', params: { id: course.id } }"
                    class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-4 py-2.5 text-center text-sm font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 active:scale-[0.98] sm:w-auto"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                    </svg>
                    Открыть конструктор
                  </RouterLink>

                  <RouterLink
                    :to="{ name: 'quiz-editor', params: { id: course.id } }"
                    class="group/action relative inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-violet-500/20 bg-violet-500/10 text-violet-200 transition hover:bg-violet-500 hover:text-white"
                    aria-label="Управлять тестами"
                  >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M8 6h12M8 12h12M8 18h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                      <path d="M4 6h.01M4 12h.01M4 18h.01" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
                    </svg>
                    <span class="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs font-bold text-slate-200 opacity-0 shadow-xl transition group-hover/action:opacity-100">
                      Управлять тестами
                    </span>
                  </RouterLink>

                  <RouterLink
                    :to="{ name: 'course-detail', params: { id: course.id } }"
                    class="group/action relative inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/70 text-slate-300 transition hover:border-sky-400/60 hover:text-sky-200"
                    aria-label="Предпросмотр курса"
                  >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                      <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" stroke="currentColor" stroke-width="1.8" />
                    </svg>
                    <span class="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs font-bold text-slate-200 opacity-0 shadow-xl transition group-hover/action:opacity-100">
                      Предпросмотр
                    </span>
                  </RouterLink>

                  <button
                    class="group/action relative inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-700 bg-slate-800/70 text-slate-300 transition hover:border-amber-400/60 hover:text-amber-200"
                    type="button"
                    aria-label="Редактировать курс"
                    @click="openEditModal(course)"
                  >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M4 20h4l10.5-10.5a2.12 2.12 0 0 0-3-3L5 17v3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                      <path d="m14 7 3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                    </svg>
                    <span class="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs font-bold text-slate-200 opacity-0 shadow-xl transition group-hover/action:opacity-100">
                      Редактировать
                    </span>
                  </button>

                  <button
                    class="group/action relative inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-200 transition hover:bg-rose-500 hover:text-white"
                    type="button"
                    aria-label="Удалить курс"
                    @click="openDeleteCourse(course)"
                  >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M6 7h12M10 7V5h4v2M9 10v7M15 10v7M8 7l1 13h6l1-13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <span class="pointer-events-none absolute -top-10 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs font-bold text-slate-200 opacity-0 shadow-xl transition group-hover/action:opacity-100">
                      Удалить
                    </span>
                  </button>
                </div>
              </div>

              <div class="mt-5 grid gap-3 sm:grid-cols-3">
                <div class="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Модули</p>
                  <strong class="mt-1 block text-2xl font-black text-slate-100">{{ getModuleCount(course) }}</strong>
                </div>
                <div class="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Уроки</p>
                  <strong class="mt-1 block text-2xl font-black text-slate-100">{{ getLessonCount(course) }}</strong>
                </div>
                <div class="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                  <p class="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Обновлено</p>
                  <strong class="mt-1 block truncate text-sm font-black text-slate-200">{{ formatDate(course.updated_at || course.created_at) }}</strong>
                </div>
              </div>

              <div class="mt-5 flex flex-wrap gap-2">
                <span
                  v-for="skill in getCourseSkills(course).slice(0, 8)"
                  :key="getSkillId(skill)"
                  class="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-200"
                >
                  {{ getSkillName(skill) }}
                </span>
                <span v-if="getCourseSkills(course).length > 8" class="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-bold text-slate-400">
                  +{{ getCourseSkills(course).length - 8 }}
                </span>
                <span v-if="!getCourseSkills(course).length" class="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-bold text-slate-500">
                  Навыки не указаны
                </span>
              </div>
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="isModalOpen" class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/85 p-3 backdrop-blur-sm sm:p-4" @click.self="closeCourseModal">
      <div class="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-[2rem] border border-slate-700 bg-slate-900 shadow-2xl shadow-slate-950/50">
        <div class="sticky top-0 z-10 border-b border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:px-6 sm:py-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.22em] text-indigo-300">{{ isEditMode ? 'Редактирование' : 'Создание' }}</p>
              <h2 class="mt-1 text-2xl font-black text-slate-50">{{ isEditMode ? 'Настройки курса' : 'Новый курс' }}</h2>
            </div>
            <button class="rounded-2xl border border-slate-700 bg-slate-800/70 p-2 text-slate-300 transition hover:text-white" type="button" @click="closeCourseModal">
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </div>

        <form class="overflow-y-auto px-4 py-5 sm:px-6 sm:py-6" @submit.prevent="saveCourse">
          <div v-if="modalError" class="mb-5 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm font-semibold text-rose-100">
            {{ modalError }}
          </div>

          <div class="grid gap-5">
            <label class="block">
              <span class="mb-2 flex items-center justify-between text-sm font-bold text-slate-300">
                <span>Название курса</span>
                <span class="text-xs text-slate-500">{{ courseForm.title.length }}/{{ TITLE_LIMIT }}</span>
              </span>
              <input
                v-model.trim="courseForm.title"
                :maxlength="TITLE_LIMIT"
                type="text"
                required
                placeholder="Например: Backend-разработка на Django"
                class="w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
              >
            </label>

            <label class="block">
              <span class="mb-2 flex items-center justify-between text-sm font-bold text-slate-300">
                <span>Описание</span>
                <span class="text-xs text-slate-500">{{ courseForm.description.length }}/{{ DESCRIPTION_LIMIT }}</span>
              </span>
              <textarea
                ref="descriptionTextarea"
                v-model="courseForm.description"
                :maxlength="DESCRIPTION_LIMIT"
                required
                rows="3"
                placeholder="Кратко опишите цель курса, аудиторию и результат обучения."
                class="min-h-[96px] w-full resize-none rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                @input="autoGrowTextarea"
              ></textarea>
            </label>

            <div class="rounded-3xl border border-slate-800 bg-slate-950/40 p-4">
              <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm font-bold text-slate-300">Обложка курса</p>
                  <p class="mt-1 text-xs leading-5 text-slate-500">JPG, PNG или WebP до {{ IMAGE_LIMIT_MB }} МБ. Рекомендуется горизонтальное изображение.</p>
                </div>
                <label class="inline-flex w-full cursor-pointer items-center justify-center rounded-2xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-bold text-slate-200 transition hover:border-indigo-400/60 hover:text-white sm:w-auto">
                  Выбрать файл
                  <input ref="imageInputRef" type="file" accept="image/*" class="sr-only" @change="handleFileUpload">
                </label>
              </div>

              <div class="mt-4 flex items-center gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
                <div class="flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-700 bg-slate-950 text-slate-500">
                  <img v-if="currentImageUrl && !selectedImageName" :src="currentImageUrl" alt="Текущая обложка" class="h-full w-full object-cover">
                  <svg v-else class="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 16.5v-9Z" stroke="currentColor" stroke-width="1.8" />
                    <path d="m7 15 3-3 2 2 2-2 3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </div>
                <div class="min-w-0">
                  <p class="truncate text-sm font-bold text-slate-200">
                    {{ selectedImageName || (currentImageUrl ? 'Используется текущая обложка' : 'Файл не выбран') }}
                  </p>
                  <p class="mt-1 text-xs text-slate-500">При сохранении новая обложка заменит текущую.</p>
                </div>
              </div>
            </div>

            <div class="rounded-3xl border border-slate-800 bg-slate-950/40 p-4">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p class="text-sm font-bold text-slate-300">Навыки курса</p>
                  <p class="mt-1 text-xs leading-5 text-slate-500">Выберите компетенции, которые студент получит после прохождения.</p>
                </div>
                <input
                  v-model="skillSearch"
                  type="search"
                  placeholder="Поиск навыка"
                  class="w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-indigo-400 sm:w-56"
                >
              </div>

              <div v-if="selectedSkillsPreview.length" class="mt-4 flex flex-wrap gap-2 border-b border-slate-800 pb-4">
                <span
                  v-for="skill in selectedSkillsPreview"
                  :key="skill.id"
                  class="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-bold text-indigo-200"
                >
                  {{ skill.name }}
                </span>
              </div>

              <div v-if="filteredSkills.length" class="mt-4 grid max-h-52 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
                <label
                  v-for="skill in filteredSkills"
                  :key="skill.id"
                  class="flex cursor-pointer items-center gap-3 rounded-2xl border px-3 py-2.5 transition"
                  :class="courseForm.skills_covered.includes(skill.id) ? 'border-indigo-400/50 bg-indigo-500/10 text-indigo-100' : 'border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-600'"
                >
                  <input
                    v-model="courseForm.skills_covered"
                    type="checkbox"
                    :value="skill.id"
                    class="h-4 w-4 rounded border-slate-600 bg-slate-950 text-indigo-500 focus:ring-indigo-500"
                  >
                  <span class="truncate text-sm font-semibold">{{ skill.name }}</span>
                </label>
              </div>

              <div v-else class="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100">
                {{ availableSkills.length ? 'По этому запросу навыки не найдены.' : 'Навыки пока не добавлены в систему.' }}
              </div>
            </div>
          </div>
        </form>

        <div class="sticky bottom-0 z-10 flex flex-col-reverse gap-3 border-t border-slate-800 bg-slate-900/95 px-4 py-4 backdrop-blur sm:flex-row sm:justify-end sm:px-6 sm:py-5">
          <button
            class="rounded-2xl border border-slate-700 bg-slate-800 px-5 py-3 text-sm font-bold text-slate-300 transition hover:bg-slate-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            :disabled="isSaving"
            @click="closeCourseModal"
          >
            Отмена
          </button>
          <button
            class="rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            :disabled="isSaving"
            @click="saveCourse"
          >
            {{ isSaving ? 'Сохранение...' : (isEditMode ? 'Сохранить изменения' : 'Создать курс') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="confirmDialog.open" class="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/85 p-4 backdrop-blur-sm" @click.self="closeConfirmDialog">
      <div class="w-full max-w-md rounded-[2rem] border border-slate-700 bg-slate-900 p-6 shadow-2xl shadow-slate-950/50">
        <div class="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-200">
          <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 8v5M12 16.5h.01M10.2 4.7 2.8 17.5A2 2 0 0 0 4.5 20h15a2 2 0 0 0 1.7-2.5L13.8 4.7a2 2 0 0 0-3.6 0Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
        <h3 class="text-xl font-black text-slate-50">{{ confirmDialog.title }}</h3>
        <p class="mt-3 text-sm leading-6 text-slate-400">{{ confirmDialog.message }}</p>
        <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            class="rounded-2xl border border-slate-700 bg-slate-800 px-5 py-3 text-sm font-bold text-slate-300 transition hover:bg-slate-700 disabled:opacity-60"
            type="button"
            :disabled="confirmDialog.pending"
            @click="closeConfirmDialog"
          >
            Отмена
          </button>
          <button
            class="rounded-2xl bg-rose-600 px-5 py-3 text-sm font-black text-white transition hover:bg-rose-500 disabled:opacity-60"
            type="button"
            :disabled="confirmDialog.pending"
            @click="confirmAction"
          >
            {{ confirmDialog.pending ? 'Удаление...' : confirmDialog.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
