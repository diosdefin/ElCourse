<script setup>
import { computed, onMounted, ref } from 'vue'

import api from '../api'

const API_BASE_URL = 'http://127.0.0.1:8000'

const students = ref([])
const myOffers = ref([])
const loading = ref(true)
const pageError = ref('')
const banner = ref({ type: '', message: '' })

const searchTerm = ref('')
const skillInput = ref('')
const selectedSkills = ref([])
const resumeLoadingId = ref(null)

const profileModal = ref({ isOpen: false, student: null })
const offerModal = ref({
  isOpen: false,
  student: null,
  message: '',
  contact: '',
  submitting: false,
  error: '',
})

const normalizeValue = (value = '') => value.toString().trim().toLowerCase()


const getStudentSkillNames = (student) => {
  if (!Array.isArray(student?.skills)) {
    return []
  }

  return student.skills
    .map((skill) => (typeof skill === 'string' ? skill : skill?.name))
    .filter(Boolean)
}

const getAvatarUrl = (student) => (student?.avatar ? `${API_BASE_URL}${student.avatar}` : null)

const availableSkills = computed(() => {
  const counters = new Map()

  for (const student of students.value) {
    for (const skill of getStudentSkillNames(student)) {
      counters.set(skill, (counters.get(skill) || 0) + 1)
    }
  }

  return [...counters.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([name, count]) => ({ name, count }))
})

const latestOfferByStudentId = computed(() => {
  const map = new Map()

  for (const offer of myOffers.value) {
    if (!map.has(offer.student)) {
      map.set(offer.student, offer)
    }
  }

  return map
})

const getStudentOffer = (studentId) => latestOfferByStudentId.value.get(studentId) || null

const getOfferStatusMeta = (studentId) => {
  const offer = getStudentOffer(studentId)
  if (!offer) {
    return null
  }

  if (offer.status === 'pending') {
    return {
      title: 'Оффер уже отправлен',
      subtitle: 'Ожидает ответа',
      icon: '⏳',
      className: 'bg-slate-900/90 border-slate-700 text-slate-300',
    }
  }

  if (offer.status === 'accepted') {
    return {
      title: 'Оффер принят',
      subtitle: 'Повторная отправка не нужна',
      icon: '✅',
      className: 'bg-slate-900/90 border-slate-700 text-slate-200',
    }
  }

  return null
}

const hasLockedOffer = (studentId) => Boolean(getOfferStatusMeta(studentId))

const matchesSkill = (skillName, query) => normalizeValue(skillName).includes(normalizeValue(query))

const isSelectedSkill = (skillName) =>
  selectedSkills.value.some((tag) => normalizeValue(tag) === normalizeValue(skillName))

const resolveSkillLabel = (rawSkill) => {
  const trimmedSkill = rawSkill.trim()
  if (!trimmedSkill) {
    return null
  }

  const existingSkill = availableSkills.value.find(
    ({ name }) =>
      matchesSkill(name, trimmedSkill) || normalizeValue(trimmedSkill).includes(normalizeValue(name))
  )

  return existingSkill?.name || trimmedSkill
}

const addSkillTagsFromInput = () => {
  const tags = skillInput.value
    .split(',')
    .map((tag) => resolveSkillLabel(tag))
    .filter(Boolean)

  if (!tags.length) {
    return
  }

  const nextTags = [...selectedSkills.value]
  for (const tag of tags) {
    if (!nextTags.some((selectedTag) => normalizeValue(selectedTag) === normalizeValue(tag))) {
      nextTags.push(tag)
    }
  }

  selectedSkills.value = nextTags
  skillInput.value = ''
}

const removeSkillTag = (tagToRemove) => {
  selectedSkills.value = selectedSkills.value.filter(
    (tag) => normalizeValue(tag) !== normalizeValue(tagToRemove)
  )
}

const toggleSkillTag = (skillName) => {
  if (isSelectedSkill(skillName)) {
    removeSkillTag(skillName)
    return
  }

  selectedSkills.value = [...selectedSkills.value, skillName]
}

const handleSkillInputKeydown = (event) => {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addSkillTagsFromInput()
  }
}

const clearFilters = () => {
  searchTerm.value = ''
  skillInput.value = ''
  selectedSkills.value = []
}

const filteredStudents = computed(() => {
  const normalizedQuery = normalizeValue(searchTerm.value)

  return students.value.filter((student) => {
    const skillNames = getStudentSkillNames(student)
    const searchableParts = [student.username, student.email, student.bio, ...skillNames]

    const matchesText =
      !normalizedQuery ||
      searchableParts.some((part) => normalizeValue(part).includes(normalizedQuery))

    const matchesSkills =
      selectedSkills.value.length === 0 ||
      selectedSkills.value.every((tag) =>
        skillNames.some((skillName) => matchesSkill(skillName, tag))
      )

    return matchesText && matchesSkills
  })
})

const fetchData = async ({ silent = false } = {}) => {
  if (!silent) {
    loading.value = true
  }
  pageError.value = ''
  try {
    const [studentsRes, offersRes] = await Promise.all([
      api.get('/employer/search/'),
      api.get('/employer/offers/'),
    ])
    students.value = studentsRes.data
    myOffers.value = offersRes.data
  } catch (error) {
    console.error('Ошибка загрузки данных работодателя:', error)
    pageError.value = 'Не удалось загрузить базу талантов. Попробуйте обновить страницу.'
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

const openProfile = (student) => {
  profileModal.value = { isOpen: true, student }
}

const closeProfile = () => {
  profileModal.value = { isOpen: false, student: null }
}

const openOfferModal = (student) => {
  if (hasLockedOffer(student.id)) {
    return
  }

  banner.value = { type: '', message: '' }
  offerModal.value = {
    isOpen: true,
    student,
    message: `Здравствуйте, ${student.username}! Нам понравился ваш профиль на ELCOURSE и мы хотели бы обсудить возможное сотрудничество.`,
    contact: '',
    submitting: false,
    error: '',
  }
}

const closeOfferModal = () => {
  offerModal.value = {
    isOpen: false,
    student: null,
    message: '',
    contact: '',
    submitting: false,
    error: '',
  }
}

const openOfferFromProfile = () => {
  const selectedStudent = profileModal.value.student
  closeProfile()

  if (selectedStudent) {
    openOfferModal(selectedStudent)
  }
}

const submitOffer = async () => {
  if (!offerModal.value.student || !offerModal.value.message.trim()) {
    return
  }
  offerModal.value.submitting = true
  offerModal.value.error = ''
  try {
    await api.post('/employer/offer/', {
      student_id: offerModal.value.student.id,
      message: offerModal.value.message.trim(),
      contact_link: offerModal.value.contact.trim(),
    })
    const studentName = offerModal.value.student.username
    closeOfferModal()
    await fetchData({ silent: true })
    banner.value = {
      type: 'success',
      message: `Оффер для ${studentName} отправлен. Карточка уже защищена от повторной отправки.`,
    }
  } catch (error) {
    console.error('Ошибка отправки оффера:', error)
    offerModal.value.error =
      error.response?.data?.detail || 'Не удалось отправить оффер. Попробуйте еще раз.'
    if (error.response?.data?.existing_offer) {
      await fetchData({ silent: true })
    }
  } finally {
    offerModal.value.submitting = false
  }
}

const downloadResume = async (student) => {
  if (!student) {
    return
  }
  resumeLoadingId.value = student.id
  try {
    const response = await api.get('/resume/export/', {
      params: { user_id: student.id },
      responseType: 'blob',
    })
    const blobUrl = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.setAttribute('download', `Resume_${student.username}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrl)
  } catch (error) {
    console.error('Ошибка скачивания резюме:', error)
    window.alert('Не удалось скачать PDF-резюме студента.')
  } finally {
    resumeLoadingId.value = null
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="space-y-8 pb-20">
    <section class="relative overflow-hidden rounded-[2rem] border border-slate-700/60 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.25),_transparent_30%),linear-gradient(135deg,_rgba(15,23,42,0.98),_rgba(15,23,42,0.88))] p-8 shadow-2xl shadow-slate-950/40">
      <div class="absolute -right-12 top-6 h-40 w-40 rounded-full bg-emerald-400/10 blur-3xl"></div>
      <div class="absolute -bottom-10 left-20 h-36 w-36 rounded-full bg-indigo-500/10 blur-3xl"></div>

      <div class="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div class="max-w-2xl">
          <span class="inline-flex items-center gap-2 rounded-full border border-indigo-400/20 bg-indigo-400/10 px-4 py-1 text-xs font-bold uppercase tracking-[0.3em] text-indigo-200">
            Talent Search
          </span>
          <h1 class="mt-4 text-4xl font-black text-white sm:text-5xl">Поиск студентов без лишних дублей</h1>
          <p class="mt-4 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
            Открывайте профиль в один клик, фильтруйте кандидатов по нескольким навыкам сразу и отправляйте оффер только тем, кому он действительно еще нужен.
          </p>
        </div>

        <div class="grid gap-3 text-sm text-slate-300 sm:grid-cols-3">
          <div class="rounded-2xl border border-slate-700/70 bg-slate-900/40 px-4 py-3 backdrop-blur">
            <p class="text-xs uppercase tracking-[0.2em] text-slate-500">Кандидатов</p>
            <p class="mt-2 text-2xl font-black text-white">{{ students.length }}</p>
          </div>
          <div class="rounded-2xl border border-slate-700/70 bg-slate-900/40 px-4 py-3 backdrop-blur">
            <p class="text-xs uppercase tracking-[0.2em] text-slate-500">Активных офферов</p>
            <p class="mt-2 text-2xl font-black text-white">
              {{ myOffers.filter((offer) => offer.status === 'pending').length }}
            </p>
          </div>
          <div class="rounded-2xl border border-slate-700/70 bg-slate-900/40 px-4 py-3 backdrop-blur">
            <p class="text-xs uppercase tracking-[0.2em] text-slate-500">Совпадений</p>
            <p class="mt-2 text-2xl font-black text-white">{{ filteredStudents.length }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-[1.15fr,0.95fr]">
      <div class="rounded-[1.75rem] border border-slate-700/60 bg-slate-900/70 p-5 shadow-xl shadow-slate-950/20 backdrop-blur">
        <label class="mb-3 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
          Быстрый поиск
        </label>
        <div class="relative">
          <svg class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            v-model="searchTerm"
            type="text"
            placeholder="Имя, email или фраза из блока «О себе»"
            class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 py-4 pl-12 pr-4 text-slate-100 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          >
        </div>
      </div>

      <div class="rounded-[1.75rem] border border-slate-700/60 bg-slate-900/70 p-5 shadow-xl shadow-slate-950/20 backdrop-blur">
        <label class="mb-3 block text-xs font-bold uppercase tracking-[0.25em] text-slate-500">
          Мульти-поиск по навыкам
        </label>
        <div class="flex gap-3">
          <input
            v-model="skillInput"
            type="text"
            placeholder="Python, Vue.js, Django"
            class="flex-1 rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-4 text-slate-100 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/30"
            @keydown="handleSkillInputKeydown"
            @blur="addSkillTagsFromInput"
          >
          <button
            class="rounded-2xl bg-indigo-600 px-5 py-4 text-sm font-bold text-white transition hover:bg-indigo-500"
            @click="addSkillTagsFromInput"
          >
            Добавить
          </button>
        </div>
      </div>
    </section>

    <section class="rounded-[1.75rem] border border-slate-700/60 bg-slate-900/60 p-5 shadow-xl shadow-slate-950/20 backdrop-blur">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Популярные навыки</p>
          <p class="mt-2 text-sm text-slate-400">Нажмите несколько тегов, чтобы оставить только тех, кто знает все выбранные технологии.</p>
        </div>

        <button
          v-if="searchTerm || skillInput || selectedSkills.length"
          class="rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-slate-500 hover:text-white"
          @click="clearFilters"
        >
          Сбросить фильтры
        </button>
      </div>

      <div class="mt-5 flex flex-wrap gap-2">
        <button
          v-for="skill in availableSkills.slice(0, 14)"
          :key="skill.name"
          class="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition"
          :class="isSelectedSkill(skill.name)
            ? 'border-emerald-400/40 bg-emerald-500/15 text-emerald-300'
            : 'border-slate-700 bg-slate-950/60 text-slate-300 hover:border-slate-500 hover:text-white'"
          @click="toggleSkillTag(skill.name)"
        >
          {{ skill.name }}
          <span class="rounded-full bg-black/20 px-2 py-0.5 text-[11px] text-slate-400">{{ skill.count }}</span>
        </button>
      </div>

      <div v-if="selectedSkills.length" class="mt-5 flex flex-wrap gap-2 border-t border-slate-800 pt-5">
        <span
          v-for="tag in selectedSkills"
          :key="tag"
          class="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/15 px-4 py-2 text-sm font-semibold text-indigo-200"
        >
          {{ tag }}
          <button class="text-indigo-200 transition hover:text-white" @click="removeSkillTag(tag)">
            ×
          </button>
        </span>
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

    <div v-if="loading" class="rounded-[1.75rem] border border-slate-800 bg-slate-900/50 px-6 py-20 text-center text-slate-400">
      Загружаем базу талантов...
    </div>

    <div
      v-else-if="pageError"
      class="rounded-[1.75rem] border border-rose-500/20 bg-rose-500/10 px-6 py-10 text-center text-rose-300"
    >
      {{ pageError }}
    </div>

    <div
      v-else-if="filteredStudents.length === 0"
      class="rounded-[1.75rem] border border-dashed border-slate-700 bg-slate-900/40 px-6 py-20 text-center"
    >
      <p class="text-xl font-bold text-slate-200">Ничего не найдено</p>
      <p class="mt-2 text-sm text-slate-500">Попробуйте убрать часть тегов или изменить запрос.</p>
    </div>

    <section v-else class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="student in filteredStudents"
        :key="student.id"
        class="card-hover flex h-full cursor-pointer flex-col rounded-[1.75rem] border border-slate-700/70 bg-slate-900/70 p-6 shadow-xl shadow-slate-950/20 backdrop-blur"
        tabindex="0"
        @click="openProfile(student)"
        @keydown.enter.prevent="openProfile(student)"
        @keydown.space.prevent="openProfile(student)"
      >
        <div class="flex items-start gap-4">
          <div class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-slate-700 bg-slate-800">
            <img
              v-if="getAvatarUrl(student)"
              :src="getAvatarUrl(student)"
              :alt="student.username"
              class="h-full w-full object-cover"
            >
            <span v-else class="text-xl font-black text-slate-300">
              {{ student.username[0]?.toUpperCase() }}
            </span>
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h2 class="truncate text-xl font-black text-white">{{ student.username }}</h2>
              <span
                v-if="student.is_verified"
                class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-sky-500/15 text-xs text-sky-300"
                title="Верифицированный профиль"
              >
                ✓
              </span>
            </div>
            <p class="mt-1 truncate text-xs uppercase tracking-[0.2em] text-slate-500">{{ student.email }}</p>
          </div>
        </div>

        <p class="mt-5 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-slate-300">
          {{ student.bio || 'Студент пока не добавил описание, но навыки уже можно проверить в профиле.' }}
        </p>

        <div class="mt-5 flex flex-wrap gap-2">
          <span
            v-for="skill in getStudentSkillNames(student).slice(0, 5)"
            :key="`${student.id}-${skill}`"
            class="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-300"
          >
            {{ skill }}
          </span>
          <span
            v-if="getStudentSkillNames(student).length > 5"
            class="rounded-full border border-slate-700 bg-slate-950/60 px-3 py-1 text-xs font-bold text-slate-400"
          >
            +{{ getStudentSkillNames(student).length - 5 }}
          </span>
        </div>

        <div class="mt-6 grid gap-3 sm:grid-cols-2">
          <button
            class="rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm font-bold text-slate-200 transition hover:border-slate-500 hover:text-white"
            @click.stop="openProfile(student)"
          >
            Быстрый просмотр
          </button>

          <div
            v-if="getOfferStatusMeta(student.id)"
            class="flex items-center justify-center rounded-2xl border px-4 py-3 text-center text-sm font-semibold"
            :class="getOfferStatusMeta(student.id).className"
          >
            <span>
              {{ getOfferStatusMeta(student.id).icon }} {{ getOfferStatusMeta(student.id).title }}
              <span class="block text-xs font-medium text-slate-400">
                {{ getOfferStatusMeta(student.id).subtitle }}
              </span>
            </span>
          </div>

          <button
            v-else
            class="rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-500"
            @click.stop="openOfferModal(student)"
          >
            Пригласить
          </button>
        </div>
      </article>
    </section>

    <div
      v-if="profileModal.isOpen && profileModal.student"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      @click.self="closeProfile"
    >
      <div class="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[2rem] border border-slate-700 bg-slate-900 shadow-2xl shadow-black/60">
        <div class="relative overflow-hidden border-b border-slate-800 p-8">
          <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.14),_transparent_35%),radial-gradient(circle_at_top_right,_rgba(99,102,241,0.18),_transparent_30%)]"></div>

          <div class="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex items-start gap-5">
              <div class="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-[1.5rem] border border-slate-700 bg-slate-800">
                <img
                  v-if="getAvatarUrl(profileModal.student)"
                  :src="getAvatarUrl(profileModal.student)"
                  :alt="profileModal.student.username"
                  class="h-full w-full object-cover"
                >
                <span v-else class="text-3xl font-black text-slate-300">
                  {{ profileModal.student.username[0]?.toUpperCase() }}
                </span>
              </div>

              <div class="pt-2">
                <div class="flex items-center gap-3">
                  <h2 class="text-3xl font-black text-white">{{ profileModal.student.username }}</h2>
                  <span
                    v-if="profileModal.student.is_verified"
                    class="inline-flex items-center rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em] text-sky-200"
                  >
                    Verified
                  </span>
                </div>
                <p class="mt-2 text-sm text-slate-400">{{ profileModal.student.email }}</p>
                <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-300">
                  {{ profileModal.student.bio || 'Студент пока не заполнил блок «О себе», но его подтвержденные навыки уже доступны ниже.' }}
                </p>
              </div>
            </div>

            <button class="self-start text-slate-500 transition hover:text-white" @click="closeProfile">
              <svg class="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="grid gap-6 p-8 lg:grid-cols-[1.2fr,0.8fr]">
          <div class="rounded-[1.5rem] border border-slate-800 bg-slate-950/40 p-6">
            <p class="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Подтвержденные навыки</p>
            <div class="mt-5 flex flex-wrap gap-2">
              <span
                v-for="skill in getStudentSkillNames(profileModal.student)"
                :key="`${profileModal.student.id}-modal-${skill}`"
                class="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300"
              >
                ✓ {{ skill }}
              </span>
              <p v-if="!getStudentSkillNames(profileModal.student).length" class="text-sm text-slate-500">
                Подтвержденных навыков пока нет.
              </p>
            </div>
          </div>

          <div class="space-y-4">
            <div class="rounded-[1.5rem] border border-slate-800 bg-slate-950/40 p-6">
              <p class="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Действия</p>
              <div class="mt-5 grid gap-3">
                <button
                  class="rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-bold text-white transition hover:border-indigo-400 hover:text-indigo-200"
                  :disabled="resumeLoadingId === profileModal.student.id"
                  @click="downloadResume(profileModal.student)"
                >
                  {{ resumeLoadingId === profileModal.student.id ? 'Подготавливаем PDF...' : '📄 Скачать резюме (PDF)' }}
                </button>

                <div
                  v-if="getOfferStatusMeta(profileModal.student.id)"
                  class="rounded-2xl border px-4 py-4 text-sm"
                  :class="getOfferStatusMeta(profileModal.student.id).className"
                >
                  <p class="font-bold">
                    {{ getOfferStatusMeta(profileModal.student.id).icon }}
                    {{ getOfferStatusMeta(profileModal.student.id).title }}
                  </p>
                  <p class="mt-1 text-xs text-slate-400">{{ getOfferStatusMeta(profileModal.student.id).subtitle }}</p>
                </div>

                <button
                  v-else
                  class="rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-indigo-500"
                  @click="openOfferFromProfile"
                >
                  Пригласить студента
                </button>

                <button
                  class="rounded-2xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 transition hover:border-slate-500 hover:text-white"
                  @click="closeProfile"
                >
                  Закрыть
                </button>
              </div>
            </div>

            <div class="rounded-[1.5rem] border border-slate-800 bg-slate-950/40 p-6">
              <p class="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">Почему это удобно</p>
              <ul class="mt-4 space-y-3 text-sm leading-6 text-slate-300">
                <li>Карточка сразу показывает, был ли уже отправлен активный оффер.</li>
                <li>Профиль открывается без перехода на другую страницу.</li>
                <li>PDF-резюме скачивается прямо из модалки.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="offerModal.isOpen && offerModal.student"
      class="fixed inset-0 z-[110] flex items-center justify-center bg-slate-950/85 p-4 backdrop-blur-md"
      @click.self="closeOfferModal"
    >
      <div class="w-full max-w-2xl rounded-[2rem] border border-slate-700 bg-slate-900 p-8 shadow-2xl shadow-black/60">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.25em] text-indigo-300">Новый оффер</p>
            <h2 class="mt-3 text-3xl font-black text-white">Приглашение для {{ offerModal.student.username }}</h2>
            <p class="mt-3 max-w-xl text-sm leading-6 text-slate-400">
              Студент увидит приглашение в уведомлениях. После отправки кнопка на карточке сменится на статус и больше не позволит задублировать оффер.
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
              placeholder="Здравствуйте! Нам понравился ваш профиль и мы хотели бы обсудить сотрудничество..."
            ></textarea>
          </div>

          <div>
            <label class="mb-2 block text-sm font-bold text-slate-300">Контакт для связи</label>
            <input
              v-model="offerModal.contact"
              type="text"
              class="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-5 py-4 text-slate-100 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-500/30"
              placeholder="t.me/hr_manager или email@company.com"
            >
          </div>

          <div
            v-if="offerModal.error"
            class="rounded-2xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300"
          >
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

<style scoped>
.card-hover {
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease;
}

.card-hover:hover,
.card-hover:focus-visible {
  transform: translateY(-6px);
  border-color: rgba(129, 140, 248, 0.45);
  box-shadow: 0 24px 60px rgba(2, 6, 23, 0.45);
  outline: none;
}
</style>
