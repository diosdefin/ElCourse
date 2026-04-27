<script setup>
import { ref, onMounted } from 'vue'

import api from '../api'

const myCourses = ref([])
const availableSkills = ref([]) // НОВОЕ: Список всех навыков из базы
const loading = ref(true)

// Состояния модального окна
const isModalOpen = ref(false)
const isEditMode = ref(false)
const currentCourseId = ref(null)

const newCourse = ref({
  title: '',
  description: '',
  image: null,
  skills_covered: [] // НОВОЕ: Массив для выбранных навыков
})

const fetchMyCourses = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await api.get('/teacher/courses/')
    myCourses.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки курсов:', error)
  } finally {
    loading.value = false
  }
}

// НОВОЕ: Функция загрузки списка навыков с бэкенда
const fetchSkills = async () => {
  try {
    const response = await api.get('/skills/')
    availableSkills.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки навыков:', error)
  }
}

// Открыть модалку для СОЗДАНИЯ
const openCreateModal = () => {
  isEditMode.value = false
  newCourse.value = { title: '', description: '', image: null, skills_covered: [] }
  isModalOpen.value = true
}

// Открыть модалку для РЕДАКТИРОВАНИЯ
const openEditModal = (course) => {
  isEditMode.value = true
  currentCourseId.value = course.id
  
  // Аккуратно достаем ID навыков (если бэкенд отдает объекты, берем их .id)
  const preselectedSkills = course.skills_covered 
    ? course.skills_covered.map(s => typeof s === 'object' ? s.id : s) 
    : []

  newCourse.value = { 
    title: course.title, 
    description: course.description, 
    image: null,
    skills_covered: preselectedSkills // Подставляем уже выбранные галочки
  }
  isModalOpen.value = true
}

const handleFileUpload = (event) => {
  newCourse.value.image = event.target.files[0]
}

// Главная функция сохранения (Создание или Обновление)
const saveCourse = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const formData = new FormData()
    formData.append('title', newCourse.value.title)
    formData.append('description', newCourse.value.description)
    
    if (newCourse.value.image) {
      formData.append('image', newCourse.value.image)
    }

    // НОВОЕ: Правильно добавляем массив навыков в FormData для Django
    newCourse.value.skills_covered.forEach(skillId => {
      formData.append('skills_covered', skillId)
    })

    if (isEditMode.value) {
      await axios.patch(`http://127.0.0.1:8000/api/teacher/courses/${currentCourseId.value}/`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } else {
      await axios.post('http://127.0.0.1:8000/api/teacher/courses/', formData, {
        headers: { Authorization: `Bearer ${token}` }
      })
    }

    isModalOpen.value = false
    await fetchMyCourses()
    alert(isEditMode.value ? 'Курс обновлен!' : 'Курс создан!')
  } catch (error) {
    console.error(error)
    alert('Ошибка при сохранении курса')
  }
}

onMounted(() => {
  fetchMyCourses()
  fetchSkills() // НОВОЕ: Загружаем навыки при открытии страницы
})
</script>

<template>
  <div class="max-w-6xl mx-auto mt-8 px-4">
    <div class="flex justify-between items-center mb-10">
      <div>
        <h1 class="text-4xl font-black text-slate-100">Кабинет автора</h1>
        <p class="text-slate-500 mt-2">Управление контентом и аналитика</p>
      </div>
      <button 
        @click="openCreateModal"  
        class="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-2xl transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
      >
        + Создать новый курс
      </button>
    </div>

    <div v-if="loading" class="text-center py-20 text-slate-500">Загрузка...</div>
    <div v-else class="grid gap-6">
      <div v-for="course in myCourses" :key="course.id" 
        class="bg-slate-800/30 backdrop-blur-md p-6 rounded-3xl border border-slate-700/50 flex justify-between items-center group">
        
        <div class="flex items-center gap-6">
          <div class="w-20 h-20 bg-slate-900 rounded-2xl overflow-hidden border border-slate-700">
            <img v-if="course.image" :src="course.image" class="w-full h-full object-cover">
            <div v-else class="w-full h-full bg-slate-700 flex items-center justify-center text-slate-500 text-xs">Нет фото</div>
          </div>
          <div>
            <h3 class="text-xl font-bold text-slate-100">{{ course.title }}</h3>
            <p class="text-slate-500 text-sm">Уроков: {{ course.lessons?.length || 0 }}</p>
          </div>
        </div>

        <div class="flex gap-2">
          <RouterLink :to="{ name: 'teacher-lesson-editor', params: { id: course.id } }"
            class="p-3 bg-slate-700/30 text-slate-300 rounded-xl hover:bg-indigo-600 transition-all text-sm font-bold">
            Уроки
          </RouterLink>

          <RouterLink :to="{ name: 'quiz-editor', params: { id: course.id } }"
            class="p-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl hover:bg-emerald-500 hover:text-white transition-all text-sm font-bold">
            Тесты
          </RouterLink>

          <button @click="openEditModal(course)"
            class="p-3 bg-slate-700/30 text-slate-300 rounded-xl hover:bg-amber-500 hover:text-white transition-all text-sm font-bold">
            Изменить
          </button>
        </div>
      </div>
    </div>

    <div v-if="isModalOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div class="bg-slate-900 border border-slate-700 w-full max-w-xl rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div class="p-8 overflow-y-auto">
          <h2 class="text-2xl font-black text-slate-100 mb-6">
            {{ isEditMode ? 'Редактировать курс' : 'Новый курс' }}
          </h2>
          
          <form @submit.prevent="saveCourse" class="space-y-5"> 
            <div>
              <label class="block text-sm font-bold text-slate-400 mb-2">Название курса</label>
              <input v-model="newCourse.title" type="text" required
                class="w-full px-5 py-3 bg-slate-800 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                placeholder="Например: Основы Python для начинающих">
            </div>

            <div>
              <label class="block text-sm font-bold text-slate-400 mb-2">Описание</label>
              <textarea v-model="newCourse.description" rows="4" required
                class="w-full px-5 py-3 bg-slate-800 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                placeholder="О чем этот курс?"></textarea>
            </div>

            <div>
              <label class="block text-sm font-bold text-slate-400 mb-2">Обложка курса</label>
              <input type="file" @change="handleFileUpload" accept="image/*"
                class="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer">
            </div>

            <div class="p-5 bg-slate-800/50 rounded-2xl border border-slate-700 mt-4">
              <label class="block text-sm font-bold text-slate-300 mb-3">Какие навыки дает курс?</label>
              
              <div v-if="availableSkills.length > 0" class="flex flex-wrap gap-3">
                <label 
                  v-for="skill in availableSkills" 
                  :key="skill.id"
                  class="flex items-center gap-2 cursor-pointer bg-slate-800 px-3 py-2 rounded-xl hover:bg-slate-700 transition-colors border border-slate-700"
                >
                  <input 
                    type="checkbox" 
                    :value="skill.id" 
                    v-model="newCourse.skills_covered"
                    class="w-4 h-4 text-indigo-500 rounded focus:ring-indigo-500 bg-slate-900 border-slate-600"
                  >
                  <span class="text-slate-300 text-sm font-medium">{{ skill.name }}</span>
                </label>
              </div>
              
              <div v-else class="text-sm text-amber-500 bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
                Навыки пока не добавлены в систему. Зайдите в панель администратора Django и создайте несколько навыков (например "Python", "Vue").
              </div>
            </div>

            <div class="flex gap-4 mt-8 pt-4 border-t border-slate-800">
              <button type="button" @click="isModalOpen = false"
                class="flex-1 px-6 py-4 bg-slate-800 text-slate-300 font-bold rounded-2xl hover:bg-slate-700 transition-all">
                Отмена
              </button>
              <button type="submit"
                class="flex-1 px-6 py-4 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-600/20">
                {{ isEditMode ? 'Сохранить изменения' : 'Создать курс' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>