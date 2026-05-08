import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import api from '../api'

export const useCourseBuilderStore = defineStore('courseBuilder', () => {
  const modules = ref([])
  const lessonsByModule = ref({})
  const selectedModuleId = ref(null)
  const isLoading = ref(false)

  const selectedModule = computed(() => modules.value.find((item) => item.id === selectedModuleId.value) || null)
  const selectedLessons = computed(() => lessonsByModule.value[selectedModuleId.value] || [])

  const setSelectedModule = (moduleId) => {
    selectedModuleId.value = moduleId
  }

  const fetchModules = async (courseId) => {
    isLoading.value = true
    try {
      const response = await api.get('/teacher/modules/', {
        params: { course_id: courseId },
      })
      modules.value = response.data
      if (!selectedModuleId.value && modules.value.length) {
        selectedModuleId.value = modules.value[0].id
      }
    } finally {
      isLoading.value = false
    }
  }

  const fetchLessons = async (courseId, moduleId) => {
    const response = await api.get(`/teacher/courses/${courseId}/lessons/`, {
      params: { module_id: moduleId },
    })
    lessonsByModule.value = {
      ...lessonsByModule.value,
      [moduleId]: response.data,
    }
  }

  const createModule = async (courseId, payload) => {
    const response = await api.post('/teacher/modules/', {
      course_id: courseId,
      title: payload.title,
      order: payload.order,
    })
    modules.value = [...modules.value, response.data].sort((a, b) => a.order - b.order)
    return response.data
  }

  const updateModule = async (moduleId, patch) => {
    const response = await api.patch(`/teacher/modules/${moduleId}/`, patch)
    modules.value = modules.value.map((item) => (item.id === moduleId ? response.data : item))
    return response.data
  }

  const deleteModule = async (moduleId) => {
    await api.delete(`/teacher/modules/${moduleId}/`)
    modules.value = modules.value.filter((item) => item.id !== moduleId)
    const nextLessons = { ...lessonsByModule.value }
    delete nextLessons[moduleId]
    lessonsByModule.value = nextLessons

    if (selectedModuleId.value === moduleId) {
      selectedModuleId.value = modules.value[0]?.id || null
    }
  }

  const reorderModules = async (courseId, moduleIds) => {
    await api.post(`/teacher/courses/${courseId}/reorder-modules/`, {
      module_ids: moduleIds,
    })
    modules.value = moduleIds
      .map((id, index) => {
        const found = modules.value.find((item) => item.id === id)
        return found ? { ...found, order: index } : null
      })
      .filter(Boolean)
  }

  const createLesson = async (payload) => {
    const response = await api.post('/teacher/lessons/', payload)
    const moduleId = response.data.module_id
    const current = lessonsByModule.value[moduleId] || []
    lessonsByModule.value = {
      ...lessonsByModule.value,
      [moduleId]: [...current, response.data].sort((a, b) => a.order - b.order),
    }
    return response.data
  }

  const updateLesson = async (lessonId, patch, moduleId) => {
    const response = await api.patch(`/teacher/lessons/${lessonId}/`, patch)
    const resolvedModuleId = moduleId || response.data.module_id
    const current = lessonsByModule.value[resolvedModuleId] || []
    lessonsByModule.value = {
      ...lessonsByModule.value,
      [resolvedModuleId]: current.map((item) => (item.id === lessonId ? response.data : item)),
    }
    return response.data
  }

  const deleteLesson = async (lessonId, moduleId) => {
    await api.delete(`/teacher/lessons/${lessonId}/`)
    const current = lessonsByModule.value[moduleId] || []
    lessonsByModule.value = {
      ...lessonsByModule.value,
      [moduleId]: current.filter((item) => item.id !== lessonId),
    }
  }

  const reorderLessons = async (moduleId, lessonIds) => {
    await api.post(`/teacher/modules/${moduleId}/reorder-lessons/`, {
      lesson_ids: lessonIds,
    })
    const current = lessonsByModule.value[moduleId] || []
    lessonsByModule.value = {
      ...lessonsByModule.value,
      [moduleId]: lessonIds
        .map((id, index) => {
          const found = current.find((item) => item.id === id)
          return found ? { ...found, order: index } : null
        })
        .filter(Boolean),
    }
  }

  const getQuizConfig = async (lessonId) => {
    const response = await api.get(`/teacher/lessons/${lessonId}/quiz-config/`)
    return response.data
  }

  const saveQuizConfig = async (lessonId, payload) => {
    const response = await api.post(`/teacher/lessons/${lessonId}/quiz-config/`, payload)
    return response.data
  }

  const generateFinalExam = async (courseId) => {
    const response = await api.post(`/teacher/courses/${courseId}/generate-final-exam/`, {})
    return response.data
  }

  const fetchQuestions = async (lessonId) => {
    const response = await api.get(`/teacher/lessons/${lessonId}/questions/`)
    return response.data
  }

  const createQuestion = async (lessonId, payload) => {
    const response = await api.post(`/teacher/lessons/${lessonId}/questions/`, payload)
    return response.data
  }

  const updateQuestion = async (questionId, payload) => {
    const response = await api.patch(`/teacher/questions/${questionId}/`, payload)
    return response.data
  }

  const deleteQuestion = async (questionId) => {
    await api.delete(`/teacher/questions/${questionId}/`)
  }

  const fetchAttachments = async (lessonId) => {
    const response = await api.get(`/teacher/lessons/${lessonId}/attachments/`)
    return response.data
  }

  const uploadAttachment = async (lessonId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post(`/teacher/lessons/${lessonId}/attachments/`, formData)
    return response.data
  }

  const deleteAttachment = async (attachmentId) => {
    await api.delete(`/teacher/attachments/${attachmentId}/`)
  }

  const uploadEditorImage = async (file) => {
    const formData = new FormData()
    formData.append('image', file)
    const response = await api.post('/teacher/upload-image/', formData)
    return response.data
  }

  const uploadLessonVideo = async (lessonId, file) => {
    const formData = new FormData()
    formData.append('video', file)
    const response = await api.post(`/lessons/${lessonId}/upload-video/`, formData)
    return response.data
  }

  const getLessonVideoManifest = async (lessonId) => {
    const response = await api.get(`/lessons/${lessonId}/video/manifest/`)
    return response.data
  }

  return {
    modules,
    lessonsByModule,
    selectedModuleId,
    selectedModule,
    selectedLessons,
    isLoading,
    setSelectedModule,
    fetchModules,
    fetchLessons,
    createModule,
    updateModule,
    deleteModule,
    reorderModules,
    createLesson,
    updateLesson,
    deleteLesson,
    reorderLessons,
    getQuizConfig,
    saveQuizConfig,
    generateFinalExam,
    fetchQuestions,
    createQuestion,
    updateQuestion,
    deleteQuestion,
    fetchAttachments,
    uploadAttachment,
    deleteAttachment,
    uploadEditorImage,
    uploadLessonVideo,
    getLessonVideoManifest,
  }
})
