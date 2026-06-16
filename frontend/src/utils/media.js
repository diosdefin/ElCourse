export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = 'https://api.elcourse.app'

export const resolveMediaUrl = (value) => {
  if (!value) return '/default-avatar.png'

  let strValue = String(value).trim()

  // ЕСЛИ У ДАНИЭЛЯ ИЛИ НАЗГУЛЬ ЗАСТРЯЛ ЛОКАЛЬНЫЙ АДРЕС В БАЗЕ:
  if (strValue.includes('127.0.0.1:8000') || strValue.includes('localhost:8000')) {
    // Насильно перенаправляем его на твой рабочий сервер!
    strValue = strValue.replace('http://127.0.0.1:8000', 'https://api.elcourse.app')
    strValue = strValue.replace('http://localhost:8000', 'https://api.elcourse.app')
    return strValue
  }

  // Если ссылка уже нормальная и полная, отдаем её сразу
  if (strValue.startsWith('http://') || strValue.startsWith('https://') || strValue.startsWith('blob:')) {
    return strValue
  }

  // Если пришел просто относительный путь (например /media/avatars/...)
  const cleanPath = strValue.startsWith('/') ? strValue : `/${strValue}`
  return `${MEDIA_BASE_URL}${cleanPath}`
}