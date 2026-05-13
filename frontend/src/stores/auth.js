import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'
import { resolveMediaUrl } from '../utils/media'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || null)
  const role = ref(localStorage.getItem('user_role') || null)
  const user = ref(null)

  const isAuthenticated = computed(() => Boolean(token.value))
  const isStudent = computed(() => role.value === 'student')
  const isTeacher = computed(() => role.value === 'teacher')
  const isEmployer = computed(() => role.value === 'employer')

  const displayAvatar = computed(() => {
    if (!user.value?.avatar) {
      return null
    }
    return resolveMediaUrl(user.value.avatar)
  })

  const displayInitial = computed(() => {
    if (user.value?.username) {
      return user.value.username.charAt(0).toUpperCase()
    }
    return 'U'
  })

  function setUser(payload) {
    user.value = payload ? { ...payload } : null
    if (payload?.role) {
      role.value = payload.role
      localStorage.setItem('user_role', payload.role)
    }
  }

  function login(newToken, userRole, userPayload = null) {
    token.value = newToken
    role.value = userRole

    localStorage.setItem('access_token', newToken)
    localStorage.setItem('user_role', userRole)

    if (userPayload) {
      setUser(userPayload)
    }
  }

  function updateUserSettings(patch) {
    if (!user.value) {
      user.value = {}
    }
    user.value = { ...user.value, ...patch }
  }

  function logout() {
    token.value = null
    role.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')
    window.location.href = '/login'
  }

  async function initialize() {
    if (!token.value) {
      return
    }

    try {
      const response = await api.get('/users/me/', {
        withCredentials: true,
      })
      setUser(response.data)
    } catch {
      logout()
    }
  }

  return {
    token,
    role,
    user,
    isAuthenticated,
    isStudent,
    isTeacher,
    isEmployer,
    displayAvatar,
    displayInitial,
    setUser,
    login,
    updateUserSettings,
    logout,
    initialize,
  }
})
