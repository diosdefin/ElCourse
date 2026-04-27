<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import api from '../api'

const route = useRoute()
const course = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await api.get(`/courses/${route.params.id}/`)
    course.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки курса:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div></div>

  <div v-else-if="course" class="max-w-5xl mx-auto mt-8 px-4">
    <div class="bg-slate-800/40 backdrop-blur-md rounded-3xl shadow-xl border border-slate-700/50 overflow-hidden mb-12">
      <div class="h-40 bg-gradient-to-r from-indigo-900 to-slate-800 relative"></div>
      <div class="p-8 relative">
        <h1 class="text-4xl font-black text-slate-100 mb-2">{{ course.title }}</h1>
        <p class="text-indigo-400 font-medium mb-6">Автор: {{ course.author_name }}</p>
        <p class="text-slate-400 leading-relaxed max-w-3xl mb-8">{{ course.description }}</p>
        <div class="flex flex-wrap gap-2">
          <span v-for="skill in course.skills_covered" :key="skill.id" 
                class="px-3 py-1 bg-indigo-500/10 text-indigo-300 rounded-lg text-xs font-bold border border-indigo-500/20">
            {{ skill.name }}
          </span>
        </div>
      </div>
    </div>

    <h2 class="text-2xl font-bold text-slate-100 mb-8 flex items-center gap-3">
      Программа обучения
      <span class="text-sm font-normal text-slate-500 bg-slate-800 px-3 py-1 rounded-full">{{ course.lessons.length }} уроков</span>
    </h2>
    
    <div class="space-y-4">
      <div v-for="(lesson, index) in course.lessons" :key="lesson.id" 
           class="group bg-slate-800/30 backdrop-blur-sm p-6 rounded-2xl border transition-all duration-300 flex justify-between items-center"
           :class="lesson.is_completed ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-slate-700/50 hover:border-indigo-500/50 shadow-lg'">
        
        <div class="flex items-center gap-5">
          <div v-if="lesson.is_completed" class="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
            ✓
          </div>
          <div v-else class="w-10 h-10 rounded-full bg-slate-700 text-slate-400 flex items-center justify-center font-bold">
            {{ index + 1 }}
          </div>
          
          <div>
            <h4 class="text-lg font-bold" :class="lesson.is_completed ? 'text-emerald-400/80' : 'text-slate-100'">
              {{ lesson.title }}
            </h4>
            <span v-if="lesson.is_completed" class="text-xs text-emerald-500/70 font-medium uppercase tracking-wider">Пройдено</span>
            <span v-else class="text-xs text-slate-500 font-medium uppercase tracking-wider">Доступно</span>
          </div>
        </div>

        <RouterLink 
          :to="{ name: 'lesson-detail', params: { courseId: course.id, lessonId: lesson.id }}" 
          class="px-6 py-2 rounded-xl text-sm font-bold transition-all"
          :class="lesson.is_completed 
            ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-white' 
            : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-600/20'">
          {{ lesson.is_completed ? 'Повторить' : 'Смотреть' }}
        </RouterLink>
      </div>
    </div>

    <!-- ДОБАВЛЕННЫЙ БЛОК: Финальная аттестация -->
    <div class="mt-12 p-8 bg-indigo-500/5 rounded-3xl border border-indigo-500/20 text-center">
      <h3 class="text-2xl font-bold text-slate-100 mb-4">Финальная аттестация</h3>
      <p class="text-slate-400 mb-8 max-w-xl mx-auto">
        После прохождения всех уроков вам станет доступен тест. Успешная сдача автоматически добавит навыки курса в ваш профиль.
      </p>

      <RouterLink 
        v-if="course.progress_percentage === 100"
        :to="{ name: 'course-quiz', params: { id: course.id }}"
        class="inline-block px-10 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-2xl transition-all shadow-xl shadow-indigo-600/30"
      >
        Начать тестирование
      </RouterLink>
      
      <div v-else class="inline-block px-10 py-4 bg-slate-800 text-slate-500 rounded-2xl font-bold cursor-not-allowed border border-slate-700">
        Завершите все уроки ({{ course.progress_percentage || 0 }}%)
      </div>
    </div>
  </div>
</template>