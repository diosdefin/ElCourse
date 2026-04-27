import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  // 1. Берем данные из localStorage сразу при создании стора
  const token = ref(localStorage.getItem('access_token') || null)
  const role = ref(localStorage.getItem('user_role') || null)

  // 2. Умная проверка авторизации
  const isAuthenticated = computed(() => !!token.value)

  // 3. Геттеры для ролей (теперь они точно видят правильную переменную)
  const isStudent = computed(() => role.value === 'student')
  const isTeacher = computed(() => role.value === 'teacher')
  const isEmployer = computed(() => role.value === 'employer')

  // 4. Функция ВХОДА
  // Переименовал параметр в userRole, чтобы не путать с ref-переменной role
  function login(newToken, userRole) {
    token.value = newToken
    role.value = userRole // Обновляем нашу реактивную переменную

    localStorage.setItem('access_token', newToken)
    localStorage.setItem('user_role', userRole)

    // api.js теперь сам добавляет Authorization
  }

  // 5. Функция ВЫХОДА
  function logout() {
    token.value = null
    role.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
    // api.js теперь сам убирает Authorization
    window.location.href = '/login'
  }

  // 6. Функция ИНИЦИАЛИЗАЦИИ
  function initialize() {
    if (token.value) {
      // api.js теперь сам добавляет Authorization
    }
  }

  return {
    token,
    role,
    isAuthenticated,
    isStudent,
    isTeacher,
    isEmployer,
    login,
    logout,
    initialize
  }
})