
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const MEDIA_BASE_URL = API_BASE_URL
  .replace(/\/api\/?$/, '')
  .replace(/\/$/, '')

export const resolveMediaUrl = (value) => {
  if (!value) return ''

  // Превращаем в строку на случай, если прилетел объект, и убираем лишние пробелы
  const strValue = String(value).trim()

  // Если в строке ДВАЖДЫ повторился домен api.elcourse.app (баг Кодекса)
  if (strValue.includes('https://api.elcourse.app/media/https://api.elcourse.app/media/')) {
    return strValue.replace('https://api.elcourse.app/media/https://api.elcourse.app/media/', 'https://api.elcourse.app/media/')
  }

  // Если строка УЖЕ начинается с http:// или https://, возвращаем её КАК ЕСТЬ
  if (strValue.startsWith('http://') || strValue.startsWith('https://') || strValue.startsWith('blob:')) {
    return strValue
  }

  // Для локальной разработки, если бэкенд успел выдать полную ссылку localhost
  if (strValue.includes('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/')) {
     return strValue.replace('http://127.0.0.1:8000/media/http://127.0.0.1:8000/media/', 'http://127.0.0.1:8000/media/')
  }

  // Во всех остальных случаях склеиваем с базовым URL
  return `${MEDIA_BASE_URL}${strValue.startsWith('/') ? strValue : `/${strValue}`}`
}