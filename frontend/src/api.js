import axios from 'axios'

import { showInfo } from './utils/toast'

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
})

let handlingUnauthorized = false
let unauthorizedRedirectHandler = null

export const setUnauthorizedHandler = (handler) => {
  unauthorizedRedirectHandler = typeof handler === 'function' ? handler : null
}

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
