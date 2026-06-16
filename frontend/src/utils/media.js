
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = API_BASE_URL
  .replace(/\/api\/?$/, '')
  .replace(/\/$/, '')

export const resolveMediaUrl = (value) => {
  if (!value) return ''

  let strValue = String(value).trim()

  // Жёстко вырезаем дублирование, если оно склеилось
  if (strValue.includes('https://api.elcourse.app/media/https://api.elcourse.app/media/')) {
    strValue = strValue.replace('https://api.elcourse.app/media/https://api.elcourse.app/media/', 'https://api.elcourse.app/media/')
  }

  // Если ссылка уже нормальная и полная — отдаем её как есть
  if (strValue.startsWith('http://') || strValue.startsWith('https://') || strValue.startsWith('blob:')) {
    return strValue
  }

  // На случай локалки
  if (strValue.includes('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/')) {
    strValue = strValue.replace('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/', 'http://127.0.0.1:8000/media/')
  }

  return `${MEDIA_BASE_URL}${strValue.startsWith('/') ? strValue : `/${strValue}`}`
}