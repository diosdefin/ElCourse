export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = API_BASE_URL
  .replace(/\/api\/?$/, '')
  .replace(/\/$/, '')

export const resolveMediaUrl = (value) => {
  if (!value) return ''

  let strValue = String(value).trim()

  // Если строка уже является полной ссылкой, отдаем её как есть
  if (strValue.startsWith('http://') || strValue.startsWith('https://') || strValue.startsWith('blob:')) {
    return strValue
  }

  // Защита от дублирования "/media//media/" или "/media/media/"
  if (strValue.startsWith('/media/media/')) {
    strValue = strValue.replace('/media/media/', '/media/')
  }
  if (strValue.startsWith('media/media/')) {
    strValue = strValue.replace('media/media/', 'media/')
  }

  // Формируем чистый относительный путь
  let cleanPath = strValue.startsWith('/') ? strValue : `/${strValue}`

  // Если MEDIA_BASE_URL (https://api.elcourse.app) уже содержит на конце /media, 
  // или cleanPath начинается с /media, следим чтобы не склеилось два раза
  return `${MEDIA_BASE_URL}${cleanPath}`
}