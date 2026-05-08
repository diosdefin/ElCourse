import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { showError } from '../utils/toast'

import CommunityView from '../views/CommunityView.vue'
import CourseDetailView from '../views/CourseDetailView.vue'
import HomeView from '../views/HomeView.vue'
import LessonView from '../views/LessonView.vue'
import LoginView from '../views/LoginView.vue'
import NotificationsView from '../views/NotificationsView.vue'
import ProfileView from '../views/ProfileView.vue'
import PublicProfileView from '../views/PublicProfileView.vue'
import QuizEditorView from '../views/QuizEditorView.vue'
import QuizView from '../views/QuizView.vue'
import SettingsView from '../views/SettingsView.vue'
import TeacherCourseBuilder from '../views/TeacherCourseBuilder.vue'
import TeacherDashboard from '../views/TeacherDashboard.vue'

const routes = [
  { path: '/register', name: 'register', component: LoginView },
  { path: '/', name: 'home', component: HomeView },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/community', name: 'community', component: CommunityView },
  { path: '/user/:username', name: 'public-profile', component: PublicProfileView },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
  { path: '/settings', name: 'settings', component: SettingsView, meta: { requiresAuth: true } },
  { path: '/course/:id', name: 'course-detail', component: CourseDetailView },
  { path: '/course/:courseId/lesson/:lessonId', name: 'lesson-detail', component: LessonView },
  { path: '/course/:id/quiz', name: 'course-quiz', component: QuizView },
  {
    path: '/teacher/course/:id/lessons',
    name: 'teacher-lesson-editor',
    component: TeacherCourseBuilder,
    meta: { requiresTeacher: true },
  },
  {
    path: '/teacher/course/:id/quiz-editor',
    name: 'quiz-editor',
    component: QuizEditorView,
    meta: { requiresTeacher: true },
  },
  {
    path: '/teacher',
    name: 'teacher-dashboard',
    component: TeacherDashboard,
    meta: { requiresTeacher: true },
  },
  {
    path: '/employer',
    name: 'employer-dashboard',
    component: CommunityView,
    meta: { requiresEmployer: true },
  },
  {
    path: '/notifications',
    name: 'notifications',
    component: NotificationsView,
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    showError('Сначала войдите в аккаунт.')
    return '/login'
  }

  if (to.meta.requiresTeacher) {
    if (authStore.isAuthenticated && authStore.isTeacher) {
      return true
    }

    showError('Доступ только для преподавателей.')
    return '/'
  }

  if (to.meta.requiresEmployer) {
    if (authStore.isAuthenticated && authStore.isEmployer) {
      return true
    }

    showError('Доступ только для работодателей.')
    return '/'
  }

  return true
})

export default router
