export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = API_BASE_URL
  .replace(/\/api\/?$/, '')
  .replace(/\/$/, '')

export const resolveMediaUrl = (value) => {
  if (!value) return ''

  // 1. Принудительно переводим в строку и убираем пробелы
  let strValue = String(value).trim()

  // 2. ЕСЛИ КОДЕКС СДЕЛАЛ ДВОЙНОЙ ДОМЕН (Твой баг со скриншота)
  if (strValue.includes('https://api.elcourse.app/media/https://api.elcourse.app/media/')) {
    strValue = strValue.replace('https://api.elcourse.app/media/https://api.elcourse.app/media/', 'https://api.elcourse.app/media/')
  }

  // 3. Если после этого в строке уже есть ОДИН нормальный домен — отдаем его СРАЗУ
  if (strValue.startsWith('http://') || strValue.startsWith('https://') || strValue.startsWith('blob:')) {
    return strValue
  }

  // 4. Фикс на случай локальной разработки, если дублирует localhost
  if (strValue.includes('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/')) {
    strValue = strValue.replace('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/', 'http://127.0.0.1:8000/media/')
  }
  if (strValue.startsWith('http://127.0.0.1:8000')) {
    return strValue
  }

  // 5. Если путь остался относительным (например /media/avatars/...) - склеиваем нормально
  const cleanPath = strValue.startsWith('/') ? strValue : `/${strValue}`
  return `${MEDIA_BASE_URL}${cleanPath}`
}