import axios from 'axios'

import { API_BASE_URL } from './utils/media'
import { showInfo } from './utils/toast'

// Получаем чистый базовый адрес сервера
const rawBaseURL = import.meta.env.VITE_API_URL || API_BASE_URL || 'http://127.0.0.1:8000/'

const api = axios.create({
  // Автоматически добавляем /api/, если его забыли указать в переменной окружения
  baseURL: rawBaseURL.endsWith('/api/') ? rawBaseURL : `${rawBaseURL.replace(/\/$/, '')}/api/`,
})

let handlingUnauthorized = false
let unauthorizedRedirectHandler = null

export const setUnauthorizedHandler = (handler) => {
  unauthorizedRedirectHandler = typeof handler === 'function' ? handler : null
}

export const getTeacherActivity = (year) =>
  api.get('/teacher/activity/', {
    params: { year },
  })

export const getUserSettings = () =>
  api.get('/users/settings/', {
    withCredentials: true,
  })

export const updateUserSettings = (payload, isMultipart = false) =>
  api.patch('/users/settings/', payload, {
    withCredentials: true,
    headers: isMultipart ? { 'Content-Type': 'multipart/form-data' } : undefined,
  })

export const changePassword = (payload) =>
  api.post('/users/change-password/', payload, {
    withCredentials: true,
  })

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error?.response?.status !== 401) {
      return Promise.reject(error)
    }

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_role')

    const currentPath = window.location.pathname
    if (currentPath !== '/login' && !handlingUnauthorized) {
      handlingUnauthorized = true
      showInfo('Сессия истекла. Пожалуйста, войдите снова.')
      try {
        if (unauthorizedRedirectHandler) {
          await unauthorizedRedirectHandler()
        } else {
          window.location.assign('/login?reason=session-expired')
        }
      } finally {
        handlingUnauthorized = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
