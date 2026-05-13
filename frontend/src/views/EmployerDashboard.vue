<script setup>
import { ref, onMounted } from 'vue'

import api from '../api'
import { resolveMediaUrl } from '../utils/media'
import { showError, showSuccess } from '../utils/toast'

const students = ref([])
const searchSkills = ref('')
const loading = ref(false)

const sendOffer = async (studentId, studentName) => {
  try {
    await api.post('/employer/offer/', {
      student: studentId,
      message: 'Привет! Нам понравились твои навыки на ELCOURSE. Хотим пригласить на собеседование.'
    })

    showSuccess(`Предложение успешно отправлено студенту ${studentName}.`)
  } catch (error) {
    console.error('Ошибка отправки:', error)
    showError('Не удалось отправить предложение.')
  }
}

const searchTalents = async () => {
  loading.value = true
  try {
    const response = await api.get('/employer/search/', {
      params: {
        skills: searchSkills.value || undefined,
      },
    })
    students.value = response.data
  } catch (error) {
    console.error('Ошибка поиска:', error)
  } finally {
    loading.value = false
  }
}

const getAvatarUrl = (student) => {
  if (student.avatar) {
    return resolveMediaUrl(student.avatar)
  }
  return null
}

onMounted(searchTalents)
</script>

<template>
  <div class="mx-auto mt-8 max-w-6xl max-w-full min-w-0 px-0 sm:px-4">
    <div class="mb-12">
      <h1 class="break-words text-3xl font-black text-slate-100 sm:text-4xl">Поиск талантов</h1>
      <p class="text-slate-500 mt-2">Найдите сотрудников по подтвержденным навыкам</p>
    </div>

    <div class="mb-10 flex flex-col gap-4 rounded-3xl border border-slate-700/50 bg-slate-800/40 p-4 backdrop-blur-md sm:flex-row sm:p-6">
      <input 
        v-model="searchSkills" 
        @keyup.enter="searchTalents"
        placeholder="Введите навыки через запятую (например: Python, Vue...)" 
        class="min-w-0 flex-1 rounded-2xl border border-slate-700 bg-slate-900/50 px-4 py-4 text-white outline-none focus:ring-2 focus:ring-indigo-500 sm:px-6"
      >
      <button 
        @click="searchTalents"
        class="w-full rounded-2xl bg-indigo-600 px-8 py-4 font-bold text-white transition-all shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 sm:w-auto"
      >
        Найти
      </button>
    </div>

    <div v-if="loading" class="text-center py-20 text-indigo-400">Ищем лучших...</div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="student in students" :key="student.id" 
        class="group min-w-0 rounded-3xl border border-slate-700/50 bg-slate-800/30 p-6 backdrop-blur-sm transition-all hover:border-indigo-500/50 sm:p-8">
        
        <!-- Аватар: если есть фото показываем фото, иначе букву -->
        <div class="w-16 h-16 rounded-2xl mb-6 shadow-lg overflow-hidden">
          <img 
            v-if="getAvatarUrl(student)"
            :src="getAvatarUrl(student)"
            class="w-full h-full object-cover"
            :alt="student.username"
            @error="$event.target.style.display = 'none'"
          />
          <div 
            v-if="!getAvatarUrl(student)"
            class="w-full h-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-2xl font-black text-white"
          >
            {{ student.username.charAt(0).toUpperCase() }}
          </div>
        </div>
        
        <h3 class="mb-2 break-words text-xl font-bold text-slate-100">{{ student.username }}</h3>
        <p class="text-slate-500 text-sm mb-6">Студент платформы ELCOURSE</p>

        <div class="flex flex-wrap gap-2 mb-8">
          <span v-for="skill in student.skills" :key="skill.id" 
            class="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-bold">
            {{ skill.name }}
          </span>
        </div>

        <button 
          @click="sendOffer(student.id, student.username)"
          class="w-full py-3 bg-slate-700/50 text-white rounded-xl font-bold hover:bg-indigo-600 transition-all shadow-md active:scale-95"
        >
          Предложить работу
        </button>
      </div>
    </div>
  </div>
</template>
