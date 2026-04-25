from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Импорты общих представлений и представлений студента
from .views import (
    CourseViewSet, 
    SkillViewSet, 
    RegisterView, 
    UserProfileView,
    UserActivityView,
    CourseDetailAPIView, 
    LessonDetailAPIView, 
    CompleteLessonView,
    GetQuizView, 
    CheckQuizView, 
    StudentJobOffersView,
    NotificationCountView, 
    JobOfferUpdateView, 
    ResumeExportView,
    ProfileUpdateView
)

# Импорты кабинета преподавателя
from .teacher_views import (
    TeacherCourseListView, 
    TeacherLessonListCreateView,
    TeacherCourseDetailView, 
    TeacherQuizUpdateView
)

# Импорты кабинета работодателя
from .employer_views import (
    EmployerStudentSearchView, 
    EmployerJobOfferView, 
    EmployerOffersListView
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'skills', SkillViewSet)

urlpatterns = [
    # Базовые пути (API роутер)
    path('', include(router.urls)),
    
    # Авторизация и профиль
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('me/activity/', UserActivityView.as_view(), name='user-activity'),
    
    # Обучение (Студенты)
    path('courses/<int:pk>/', CourseDetailAPIView.as_view(), name='course-detail'),
    path('lessons/<int:pk>/', LessonDetailAPIView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/complete/', CompleteLessonView.as_view(), name='complete-lesson'),
    path('courses/<int:course_id>/quiz/', GetQuizView.as_view()),
    path('courses/<int:course_id>/quiz/check/', CheckQuizView.as_view()),
    
    # Генерация PDF-резюме (Теперь путь только один и ведет куда надо!)
    path('resume/export/', ResumeExportView.as_view(), name='resume-export'),
    
    # Кабинет Автора (Преподаватели)
    path('teacher/courses/', TeacherCourseListView.as_view(), name='teacher-courses'),
    path('teacher/courses/<int:course_id>/lessons/', TeacherLessonListCreateView.as_view(), name='teacher-lessons'),
    path('teacher/courses/<int:pk>/', TeacherCourseDetailView.as_view()),
    path('teacher/courses/<int:course_id>/quiz-editor/', TeacherQuizUpdateView.as_view()),
    
    # Поиск и офферы (Работодатели)
    path('employer/search/', EmployerStudentSearchView.as_view(), name='student-search'),
    path('employer/offer/', EmployerJobOfferView.as_view(), name='send-offer'),
    path('employer/offers/', EmployerOffersListView.as_view(), name='employer-offers'),
    
    # Уведомления и отклики (Студенты и Общие)
    path('student/offers/', StudentJobOffersView.as_view(), name='student-offers'),
    path('notifications/count/', NotificationCountView.as_view(), name='notification-count'),
    path('offers/<int:pk>/update/', JobOfferUpdateView.as_view(), name='offer-update'),


    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
]
