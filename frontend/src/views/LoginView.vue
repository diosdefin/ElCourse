<template>
  <div class="max-w-md mx-auto mt-20 px-4">
    <div class="bg-slate-800/40 backdrop-blur-xl p-10 rounded-3xl border border-slate-700/50 shadow-2xl">
      <div class="text-center mb-10">
        <div class="inline-block w-12 h-12 bg-indigo-500 rounded-2xl mb-4 flex items-center justify-center text-xl font-black text-white shadow-lg shadow-indigo-500/20">
          EL
        </div>
        <h2 class="text-3xl font-black text-slate-100 mb-2">Авторизация</h2>
        <p class="text-slate-400">Введите свои данные для входа</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label class="block text-sm font-bold text-slate-400 mb-2 ml-1">Логин</label>
          <input v-model="username" type="text" required
            class="w-full px-5 py-3 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-slate-100 transition-all placeholder:text-slate-600" 
            placeholder="Ваш логин">
        </div>

        <div>
          <label class="block text-sm font-bold text-slate-400 mb-2 ml-1">Пароль</label>
          <input v-model="password" type="password" required
            class="w-full px-5 py-3 bg-slate-900/50 border border-slate-700 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-slate-100 transition-all placeholder:text-slate-600" 
            placeholder="••••••••">
        </div>

        <button type="submit" 
          class="w-full bg-indigo-600 text-white py-4 rounded-2xl hover:bg-indigo-500 transition-all font-bold text-lg shadow-lg shadow-indigo-600/20 active:scale-95">
          Войти в аккаунт
        </button>
      </form>

      <div class="mt-8 text-center text-sm text-slate-500">
        Впервые у нас? 
        <RouterLink to="/register" class="text-indigo-400 font-bold hover:text-indigo-300 transition-colors">Создайте аккаунт</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

import api from '../api'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const router = useRouter()
const authStore = useAuthStore()

const handleLogin = async () => {
  try {
    // 1. Получаем токены через наш настроенный api
    const tokenResponse = await api.post('/token/', {
      username: username.value,
      password: password.value
    })
    
    const { access, refresh } = tokenResponse.data
    
    // 2. СРАЗУ сохраняем токены в localStorage!
    // Это критически важно: теперь наш api.js автоматически подхватит этот токен
    // для всех последующих запросов.
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    
    // 3. Получаем данные пользователя. 
    // Заметь: никаких http://127.0.0.1 и сырого axios.
    const userResponse = await api.get('/me/')
    const userRole = userResponse.data.role
    
    // 4. Обновляем глобальное хранилище Pinia
    authStore.login(access, userRole)
    
    // 5. Умная переадресация в зависимости от роли
    if (userRole === 'teacher') {
      router.push('/teacher') // Учителя сразу в кабинет
    } else {
      router.push('/profile') // Студента в профиль
    }
    
  } catch (error) {
    console.error('Ошибка входа:', error)
    // Очищаем хранилище на всякий случай, если что-то пошло не так
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    alert('Неверный логин или пароль')
  }
}

</script>