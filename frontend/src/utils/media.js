export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = API_BASE_URL
  .replace(/\/api\/?$/, '')
  .replace(/\/$/, '')

export const resolveMediaUrl = (value) => {
  if (!value) return ''
  if (/^(https?:)?\/\//i.test(value) || /^(data:|blob:)/i.test(value)) return value
  return `${MEDIA_BASE_URL}${value.startsWith('/') ? value : `/${value}`}`
}
