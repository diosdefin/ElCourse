<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '../api'

const route = useRoute()
const router = useRouter()
const lessons = ref([])
const loading = ref(true)

const newLesson = ref({
  title: '',
  video_url: '',
  content: '',
  order: 1
})

const fetchLessons = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await api.get(`/teacher/courses/${route.params.id}/lessons/`)
    lessons.value = response.data
    newLesson.value.order = lessons.value.length + 1
  } catch (error) {
    console.error('Ошибка загрузки уроков:', error)
  } finally {
    loading.value = false
  }
}

const addLesson = async () => {
  try {
    const token = localStorage.getItem('access_token')
    await api.post(`/teacher/courses/${route.params.id}/lessons/`, newLesson.value)
    // Очистка формы
    newLesson.value = { title: '', video_url: '', content: '', order: lessons.value.length + 2 }
    await fetchLessons()
    alert('Урок успешно добавлен!')
  } catch (error) {
    alert('Ошибка при добавлении урока')
  }
}

onMounted(fetchLessons)
</script>

<template>
  <div class="max-w-6xl mx-auto mt-8 px-4">
    <button @click="router.back()" class="mb-8 text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-2 font-bold">
      ← Назад в кабинет
    </button>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
      <div class="lg:col-span-1">
        <h2 class="text-2xl font-black text-slate-100 mb-6">Программа курса</h2>
        <div v-if="loading" class="text-slate-600">Загрузка...</div>
        <div v-else-if="lessons.length === 0" class="p-8 border-2 border-dashed border-slate-800 rounded-3xl text-center text-slate-600 text-sm">
          Уроков пока нет. Создайте первый!
        </div>
        <div v-else class="space-y-3">
          <div v-for="lesson in lessons" :key="lesson.id" 
               class="p-4 bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-2xl flex items-center gap-4 group hover:border-indigo-500/30 transition-all">
            <div class="w-8 h-8 rounded-lg bg-slate-700 text-slate-400 flex items-center justify-center font-bold text-xs group-hover:bg-indigo-500 group-hover:text-white transition-colors">
              {{ lesson.order }}
            </div>
            <div class="truncate">
              <p class="text-slate-200 font-bold text-sm truncate">{{ lesson.title }}</p>
              <p class="text-slate-500 text-[10px] uppercase tracking-tighter">Видео-лекция</p>
            </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2">
        <div class="bg-slate-800/20 backdrop-blur-xl p-8 rounded-[2rem] border border-slate-700/50 shadow-2xl">
          <h2 class="text-2xl font-black text-slate-100 mb-8">Добавить новый материал</h2>
          
          <form @submit.prevent="addLesson" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div class="md:col-span-3">
                <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Заголовок урока</label>
                <input v-model="newLesson.title" type="text" required
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                  placeholder="Напр: Введение в типы данных">
              </div>
              <div class="md:col-span-1">
                <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Порядок</label>
                <input v-model="newLesson.order" type="number" required
                  class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100">
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Ссылка на видео (YouTube)</label>
              <input v-model="newLesson.video_url" type="url"
                class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                placeholder="https://www.youtube.com/watch?v=...">
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase mb-2 ml-1">Текстовое содержание</label>
              <textarea v-model="newLesson.content" rows="6" required
                class="w-full px-5 py-4 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none text-slate-100"
                placeholder="Развернутый текст урока, инструкции или конспект..."></textarea>
            </div>

            <button type="submit"
              class="w-full py-5 bg-indigo-600 text-white font-black rounded-2xl hover:bg-indigo-500 transition-all shadow-xl shadow-indigo-600/20 text-lg">
              Опубликовать урок
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>