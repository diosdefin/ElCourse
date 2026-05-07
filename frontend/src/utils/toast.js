export const TOAST_EVENT_NAME = 'elcourse:toast'

export const showToast = ({ type = 'info', message = '', duration = 3800 } = {}) => {
  if (!message) {
    return
  }

  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT_NAME, {
      detail: {
        type,
        message,
        duration,
      },
    })
  )
}

export const showSuccess = (message, duration) => showToast({ type: 'success', message, duration })
export const showError = (message, duration) => showToast({ type: 'error', message, duration })
export const showInfo = (message, duration) => showToast({ type: 'info', message, duration })
