<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const questions = ref([])
const answers = ref({}) // Формат: { question_id: choice_id }
const loading = ref(true)
const result = ref(null)

onMounted(async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await axios.get(`http://127.0.0.1:8000/api/courses/${route.params.id}/quiz/`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    questions.value = response.data
  } catch (error) {
    console.error('Ошибка загрузки теста:', error)
  } finally {
    loading.value = false
  }
})

const submitQuiz = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await axios.post(`http://127.0.0.1:8000/api/courses/${route.params.id}/quiz/check/`, 
      { answers: answers.value },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    result.value = response.data
  } catch (error) {
    alert('Пожалуйста, ответьте на все вопросы')
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto mt-8 px-4">
    <h1 class="text-3xl font-black text-slate-100 mb-8 text-center">Тестирование по курсу</h1>

    <div v-if="loading" class="text-center text-slate-400">Загрузка вопросов...</div>

    <div v-else-if="!result" class="space-y-8">
      <div v-for="(q, index) in questions" :key="q.id" 
        class="bg-slate-800/40 backdrop-blur-md p-8 rounded-3xl border border-slate-700/50 shadow-xl">
        <p class="text-indigo-400 font-bold mb-2 uppercase tracking-widest text-xs">Вопрос {{ index + 1 }}</p>
        <h3 class="text-xl font-bold text-slate-100 mb-6">{{ q.text }}</h3>
        
        <div class="space-y-3">
          <label v-for="choice in q.choices" :key="choice.id" 
            class="flex items-center p-4 rounded-2xl border border-slate-700/50 cursor-pointer transition-all hover:bg-slate-700/30"
            :class="{ 'border-indigo-500 bg-indigo-500/10': answers[q.id] === choice.id }">
            <input type="radio" :name="'q'+q.id" :value="choice.id" v-model="answers[q.id]" class="hidden">
            <span class="text-slate-300 font-medium">{{ choice.text }}</span>
          </label>
        </div>
      </div>

      <button @click="submitQuiz" 
        class="w-full py-5 bg-indigo-600 hover:bg-indigo-500 text-white font-black rounded-3xl transition-all shadow-2xl shadow-indigo-600/30 text-xl">
        Завершить и проверить
      </button>
    </div>

    <div v-else class="text-center bg-slate-800/40 backdrop-blur-md p-12 rounded-3xl border border-slate-700/50 shadow-2xl">
      <div v-if="result.is_passed">
        <div class="text-6xl mb-6">🎉</div>
        <h2 class="text-3xl font-black text-emerald-400 mb-4">Поздравляем! Тест пройден.</h2>
        <p class="text-slate-400 mb-8 text-lg">Вы ответили правильно на {{ result.correct_count }} из {{ result.total_count }} вопросов. Навыки добавлены в ваш цифровой паспорт.</p>
        <RouterLink to="/profile" class="inline-block px-8 py-4 bg-emerald-600 text-white font-bold rounded-2xl">Посмотреть профиль</RouterLink>
      </div>
      <div v-else>
        <div class="text-6xl mb-6">❌</div>
        <h2 class="text-3xl font-black text-rose-500 mb-4">Нужно подтянуть знания</h2>
        <p class="text-slate-400 mb-8 text-lg">Вы ответили правильно на {{ result.correct_count }} из {{ result.total_count }}. Попробуйте еще раз!</p>
        <button @click="result = null" class="px-8 py-4 bg-slate-700 text-white font-bold rounded-2xl">Повторить тест</button>
      </div>
    </div>
  </div>
</template>