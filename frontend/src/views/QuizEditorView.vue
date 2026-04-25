<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const questions = ref([])
const newQuestion = ref({
  text: '',
  choices: [
    { text: '', is_correct: true },
    { text: '', is_correct: false },
    { text: '', is_correct: false }
  ]
})

const fetchQuiz = async () => {
  const token = localStorage.getItem('access_token')
  const res = await axios.get(`http://127.0.0.1:8000/api/teacher/courses/${route.params.id}/quiz-editor/`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  questions.value = res.data
}

const saveQuestion = async () => {
  const token = localStorage.getItem('access_token')
  await axios.post(`http://127.0.0.1:8000/api/teacher/courses/${route.params.id}/quiz-editor/`, newQuestion.value, {
    headers: { Authorization: `Bearer ${token}` }
  })
  newQuestion.value = { text: '', choices: [{ text: '', is_correct: true }, { text: '', is_correct: false }, { text: '', is_correct: false }] }
  fetchQuiz()
}

onMounted(fetchQuiz)
</script>

<template>
  <div class="max-w-4xl mx-auto mt-10 px-4">
    <h1 class="text-3xl font-black text-white mb-8">Конструктор теста</h1>

    <div class="bg-slate-800/40 p-8 rounded-3xl border border-indigo-500/30 mb-10 shadow-xl">
      <h3 class="text-xl font-bold text-slate-100 mb-6">Новый вопрос</h3>
      <input v-model="newQuestion.text" placeholder="Введите текст вопроса" class="w-full p-4 bg-slate-900 border border-slate-700 rounded-2xl text-white mb-6 outline-none focus:ring-2 focus:ring-indigo-500">
      
      <div class="space-y-3 mb-8">
        <div v-for="(choice, idx) in newQuestion.choices" :key="idx" class="flex items-center gap-4">
          <input type="radio" :name="'correct'" :checked="choice.is_correct" @change="newQuestion.choices.forEach((c, i) => c.is_correct = i === idx)" class="w-5 h-5 accent-indigo-500">
          <input v-model="choice.text" :placeholder="'Вариант ответа ' + (idx + 1)" class="flex-1 p-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white outline-none">
        </div>
      </div>

      <button @click="saveQuestion" class="w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-2xl transition-all shadow-lg shadow-emerald-600/20">
        Добавить вопрос в базу
      </button>
    </div>

    <div class="space-y-6">
      <h3 class="text-2xl font-bold text-white">Список вопросов ({{ questions.length }})</h3>
      <div v-for="q in questions" :key="q.id" class="p-6 bg-slate-800/20 border border-slate-700 rounded-2xl">
        <p class="text-slate-100 font-bold mb-4">{{ q.text }}</p>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="c in q.choices" :key="c.id" class="text-sm px-3 py-1 rounded-lg border border-slate-700" :class="{'bg-emerald-500/10 border-emerald-500/50 text-emerald-400': c.is_correct, 'text-slate-500': !c.is_correct}">
            {{ c.text }} {{ c.is_correct ? '✓' : '' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>