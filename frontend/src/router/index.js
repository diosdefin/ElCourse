import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Импорты компонентов
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import ProfileView from '../views/ProfileView.vue'
import CourseDetailView from '../views/CourseDetailView.vue'
import LessonView from '../views/LessonView.vue'
import QuizView from '../views/QuizView.vue'
import TeacherDashboard from '../views/TeacherDashboard.vue'
import LessonEditorView from '../views/LessonEditorView.vue'
import QuizEditorView from '../views/QuizEditorView.vue'
import EmployerView from '../views/EmployerView.vue'
import NotificationsView from '../views/NotificationsView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/profile', name: 'profile', component: ProfileView },
  { path: '/course/:id', name: 'course-detail', component: CourseDetailView },
  { path: '/course/:courseId/lesson/:lessonId', name: 'lesson-detail', component: LessonView },
  { path: '/course/:id/quiz', name: 'course-quiz', component: QuizView },
  {
  path: '/teacher/course/:id/lessons',
  name: 'teacher-lesson-editor',
  component: LessonEditorView,
  meta: { requiresTeacher: true }
},{ path: '/teacher/course/:id/quiz-editor', name: 'quiz-editor', component: QuizEditorView, meta: { requiresTeacher: true } },
  // ПРОВЕРЬ ЭТУ СТРОКУ ВНИМАТЕЛЬНО:
  { 
    path: '/teacher', 
    name: 'teacher-dashboard', 
    component: TeacherDashboard,
    meta: { requiresTeacher: true }
  },
  { 
    path: '/employer', 
    name: 'employer-dashboard', 
    component: EmployerView, 
    meta: { requiresEmployer: true } 
  },
  {
  path: '/notifications',
  name: 'notifications',
  component: NotificationsView,
  meta: { requiresAuth: true }
}
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes // передаем наш массив routes
})

// Защита маршрутов
router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresTeacher) {
    if (authStore.isAuthenticated && authStore.isTeacher) {
      return true // Пускаем
    } else {
      alert('Доступ только для преподавателей!')
      return '/' // Перенаправляем на главную
    }
  }

  // Если страница только для работодателей
  if (to.meta.requiresEmployer) {
    if (authStore.isAuthenticated && authStore.isEmployer) {
      return true // Пускаем
    } else {
      alert('Доступ только для работодателей!')
      return '/' // Выкидываем на главную
    }
  }
  // Для всех остальных страниц ничего возвращать не нужно (по умолчанию true)
})

console.log("Vue Router инициализирован успешно");
export default router
