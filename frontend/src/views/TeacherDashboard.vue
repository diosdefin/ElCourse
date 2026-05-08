<script setup>
import { onMounted, ref } from 'vue'

import api from '../api'
import { showError, showSuccess } from '../utils/toast'

const myCourses = ref([])
const availableSkills = ref([])
const loading = ref(true)

const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentCourseId = ref(null)

const newCourse = ref({
  title: '',
  description: '',
  image: null,
  skills_covered: [],
})

const fetchMyCourses = async () => {
  try {
    const response = await api.get('/teacher/courses/')
    myCourses.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
  } finally {
    loading.value = false
  }
}

const fetchSkills = async () => {
  try {
    const response = await api.get('/skills/')
    availableSkills.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки навыков:', error)
  }
}

const openCreateModal = () => {
  isEditMode.value = false
  newCourse.value = { title: '', description: '', image: null, skills_covered: [] }
  isModalOpen.value = true
}

const openEditModal = (course) => {
  isEditMode.value = true
  currentCourseId.value = course.id

  const preselectedSkills = course.skills_covered
    ? course.skills_covered.map((item) => (typeof item === 'object' ? item.id : item))
    : []

  newCourse.value = {
    title: course.title,
    description: course.description,
    image: null,
    skills_covered: preselectedSkills,
  }
  isModalOpen.value = true
}

const handleFileUpload = (event) => {
  newCourse.value.image = event.target.files[0]
}

const saveCourse = async () => {
  try {
    const formData = new FormData()
    formData.append('title', newCourse.value.title)
    formData.append('description', newCourse.value.description)

    if (newCourse.value.image) {
      formData.append('image', newCourse.value.image)
    }

    newCourse.value.skills_covered.forEach((skillId) => {
      formData.append('skills_covered', skillId)
    })

    if (isEditMode.value) {
      await api.patch(`/teacher/courses/${currentCourseId.value}/`, formData)
    } else {
      await api.post('/teacher/courses/', formData)
    }

    isModalOpen.value = false
    await fetchMyCourses()
    showSuccess(isEditMode.value ? 'Курс обновлен.' : 'Курс создан.')
  } catch (error) {
    console.error(error)
    showError('Ошибка при сохранении курса.')
  }
}

onMounted(() => {
  fetchMyCourses()
  fetchSkills()
})
</script>

<template>
  <div class="mx-auto mt-8 max-w-6xl px-4">
    <div class="mb-10 flex items-center justify-between">
      <div>
        <h1 class="text-4xl font-black text-slate-100">Кабинет автора</h1>
        <p class="mt-2 text-slate-500">Управление контентом</p>
      </div>
      <button
        class="rounded-2xl bg-indigo-600 px-6 py-3 font-bold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500 active:scale-95"
        @click="openCreateModal"
      >
        + Создать новый курс
      </button>
    </div>

    <div v-if="loading" class="py-20 text-center text-slate-500">Загрузка...</div>
    <div v-else class="grid gap-6">
      <div
        v-for="course in myCourses"
        :key="course.id"
        class="group flex items-center justify-between rounded-3xl border border-slate-700/50 bg-slate-800/30 p-6 backdrop-blur-md"
      >
        <div class="flex items-center gap-6">
          <div class="h-20 w-20 overflow-hidden rounded-2xl border border-slate-700 bg-slate-900">
            <img v-if="course.image" :src="course.image" class="h-full w-full object-cover">
            <div v-else class="flex h-full w-full items-center justify-center bg-slate-700 text-xs text-slate-500">Нет фото</div>
          </div>
          <div>
            <h3 class="text-xl font-bold text-slate-100">{{ course.title }}</h3>
            <p class="text-sm text-slate-500">Уроков: {{ course.lessons?.length || 0 }}</p>
          </div>
        </div>

        <div class="flex gap-2">
          <RouterLink
            :to="{ name: 'teacher-lesson-editor', params: { id: course.id } }"
            class="rounded-xl bg-slate-700/30 p-3 text-sm font-bold text-slate-300 transition-all hover:bg-indigo-600"
          >
            Конструктор
          </RouterLink>

          <RouterLink
            :to="{ name: 'quiz-editor', params: { id: course.id } }"
            class="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-400 transition-all hover:bg-emerald-500 hover:text-white"
          >
            Тесты
          </RouterLink>

          <button
            class="rounded-xl bg-slate-700/30 p-3 text-sm font-bold text-slate-300 transition-all hover:bg-amber-500 hover:text-white"
            @click="openEditModal(course)"
          >
            Изменить
          </button>
        </div>
      </div>
    </div>

    <div v-if="isModalOpen" class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <div class="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div class="overflow-y-auto p-8">
          <h2 class="mb-6 text-2xl font-black text-slate-100">
            {{ isEditMode ? 'Редактировать курс' : 'Новый курс' }}
          </h2>

          <form class="space-y-5" @submit.prevent="saveCourse">
            <div>
              <label class="mb-2 block text-sm font-bold text-slate-400">Название курса</label>
              <input
                v-model="newCourse.title"
                type="text"
                required
                class="w-full rounded-2xl border border-slate-700 bg-slate-800 px-5 py-3 text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500"
              >
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold text-slate-400">Описание</label>
              <textarea
                v-model="newCourse.description"
                rows="4"
                required
                class="w-full rounded-2xl border border-slate-700 bg-slate-800 px-5 py-3 text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500"
              ></textarea>
            </div>

            <div>
              <label class="mb-2 block text-sm font-bold text-slate-400">Обложка курса</label>
              <input
                type="file"
                accept="image/*"
                class="w-full cursor-pointer text-sm text-slate-400 file:mr-4 file:rounded-full file:border-0 file:bg-indigo-600 file:px-4 file:py-2 file:text-sm file:font-bold file:text-white hover:file:bg-indigo-500"
                @change="handleFileUpload"
              >
            </div>

            <div class="mt-4 rounded-2xl border border-slate-700 bg-slate-800/50 p-5">
              <label class="mb-3 block text-sm font-bold text-slate-300">Какие навыки дает курс?</label>

              <div v-if="availableSkills.length > 0" class="flex flex-wrap gap-3">
                <label
                  v-for="skill in availableSkills"
                  :key="skill.id"
                  class="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 transition-colors hover:bg-slate-700"
                >
                  <input
                    v-model="newCourse.skills_covered"
                    type="checkbox"
                    :value="skill.id"
                    class="h-4 w-4 rounded border-slate-600 bg-slate-900 text-indigo-500 focus:ring-indigo-500"
                  >
                  <span class="text-sm font-medium text-slate-300">{{ skill.name }}</span>
                </label>
              </div>

              <div v-else class="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-500">
                Навыки пока не добавлены в систему.
              </div>
            </div>

            <div class="mt-8 flex gap-4 border-t border-slate-800 pt-4">
              <button
                type="button"
                class="flex-1 rounded-2xl bg-slate-800 px-6 py-4 font-bold text-slate-300 transition-all hover:bg-slate-700"
                @click="isModalOpen = false"
              >
                Отмена
              </button>
              <button
                type="submit"
                class="flex-1 rounded-2xl bg-indigo-600 px-6 py-4 font-bold text-white shadow-lg shadow-indigo-600/20 transition-all hover:bg-indigo-500"
              >
                {{ isEditMode ? 'Сохранить изменения' : 'Создать курс' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
