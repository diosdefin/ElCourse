<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const courses = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/courses/')
    courses.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <div class="relative bg-gradient-to-br from-slate-800 via-indigo-900/40 to-slate-900 rounded-3xl p-12 mb-12 overflow-hidden border border-slate-800 shadow-2xl">
      <div class="absolute top-0 right-0 -mt-16 -mr-16 w-64 h-64 bg-indigo-500 opacity-10 rounded-full blur-3xl"></div>
      
      <div class="relative z-10 max-w-2xl text-white">
        <span class="inline-block px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-sm font-semibold tracking-wide mb-4 border border-indigo-500/30">
          ОБРАЗОВАТЕЛЬНАЯ ПЛАТФОРМА
        </span>
        <h1 class="text-4xl md:text-5xl font-extrabold mb-4 leading-tight text-slate-100">
          Постройте свою карьеру с новыми навыками
        </h1>
        <p class="text-lg text-slate-400 mb-8 max-w-xl">
          Проходите интерактивные курсы, получайте компетенции и формируйте свое цифровое резюме автоматически.
        </p>
      </div>
    </div>

    <div class="mb-8">
      <h2 class="text-3xl font-bold text-slate-100">Каталог программ</h2>
      <p class="text-slate-500 mt-2">Выберите направление для развития</p>
    </div>

    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      <div v-for="course in courses" :key="course.id" 
        class="group bg-slate-800/40 backdrop-blur-sm rounded-2xl shadow-xl hover:shadow-indigo-500/10 hover:-translate-y-2 transition-all duration-300 border border-slate-700/50 hover:border-indigo-500/50 overflow-hidden flex flex-col">
        
        <div class="h-48 bg-slate-800 relative overflow-hidden">
          <div v-if="course.image" class="absolute inset-0 bg-cover bg-center group-hover:scale-105 transition-transform duration-500 opacity-80" :style="`background-image: url(${course.image})`"></div>
          <div class="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent"></div>
        </div>

        <div class="p-6 flex-grow flex flex-col relative z-10 -mt-6 bg-slate-800/40 backdrop-blur-md rounded-t-2xl">
          <h3 class="text-xl font-bold text-slate-100 group-hover:text-indigo-400 transition-colors mb-3">{{ course.title }}</h3>
          <p class="text-slate-400 text-sm mb-6 line-clamp-3">{{ course.description }}</p>

          <div class="mt-auto mb-6 flex flex-wrap gap-2">
            <span v-for="skill in course.skills_covered" :key="skill.id" 
              class="px-2.5 py-1 bg-indigo-500/10 text-indigo-300 rounded-md text-xs font-semibold border border-indigo-500/20">
              {{ skill.name }}
            </span>
          </div>

          <div v-if="authStore.isAuthenticated" class="mb-6">
  <div class="flex justify-between items-center mb-2">
    <span class="text-xs font-bold text-slate-500 uppercase">Прогресс обучения</span>
    <span class="text-xs font-bold text-indigo-400">{{ course.progress_percentage }}%</span>
  </div>
  <div class="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
    <div 
      class="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-1000"
      :style="{ width: course.progress_percentage + '%' }"
    ></div>
  </div>
</div>
          <RouterLink :to="{ name: 'course-detail', params: { id: course.id }}" 
            class="w-full block text-center px-4 py-3 bg-slate-700/50 text-slate-300 font-bold rounded-xl group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
            Подробнее о курсе
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>