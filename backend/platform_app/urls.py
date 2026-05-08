from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .employer_views import EmployerJobOfferView, EmployerOffersListView, EmployerStudentSearchView
from .teacher_views import (
    GenerateFinalExamView,
    ReorderLessonsView,
    ReorderModulesView,
    TeacherLessonAttachmentDetailView,
    TeacherLessonAttachmentListCreateView,
    TeacherLessonCreateView,
    TeacherLessonDetailView,
    TeacherCourseDetailView,
    TeacherCourseListView,
    TeacherLessonListCreateView,
    TeacherLessonQuestionListCreateView,
    TeacherModuleDetailView,
    TeacherModuleListCreateView,
    TeacherQuestionDetailView,
    TeacherQuizConfigView,
    TeacherQuizUpdateView,
    TeacherUploadImageView,
)
from .views import (
    CheckQuizView,
    CommunityView,
    CompleteLessonView,
    ChangePasswordView,
    CourseDetailAPIView,
    CourseViewSet,
    FriendToggleView,
    GetQuizView,
    JobOfferUpdateView,
    LessonDetailAPIView,
    LessonVideoManifestView,
    LessonVideoUploadView,
    LessonWatchProgressView,
    NotificationCountView,
    ProfileUpdateView,
    PublicProfileView,
    PublicUserActivityView,
    RegisterView,
    ResumeExportView,
    SkillViewSet,
    StudentJobOffersView,
    TeacherActivityView,
    UserSettingsView,
    UserActivityView,
    UserProfileView,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'skills', SkillViewSet)

urlpatterns = [
    path('', include(router.urls)),

    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/', UserProfileView.as_view(), name='users-me'),
    path('users/settings/', UserSettingsView.as_view(), name='user-settings'),
    path('users/change-password/', ChangePasswordView.as_view(), name='user-change-password'),
    path('me/activity/', UserActivityView.as_view(), name='user-activity'),
    path('users/<str:username>/', PublicProfileView.as_view(), name='public-profile'),
    path('users/<str:username>/activity/', PublicUserActivityView.as_view(), name='public-user-activity'),
    path('users/<str:username>/friend/', FriendToggleView.as_view(), name='friend-toggle'),
    path('community/', CommunityView.as_view(), name='community'),

    path('courses/<int:pk>/', CourseDetailAPIView.as_view(), name='course-detail'),
    path('lessons/<int:pk>/', LessonDetailAPIView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/complete/', CompleteLessonView.as_view(), name='complete-lesson'),
    path('lessons/<int:lesson_id>/upload-video/', LessonVideoUploadView.as_view(), name='lesson-upload-video'),
    path('lessons/<int:lesson_id>/video/manifest/', LessonVideoManifestView.as_view(), name='lesson-video-manifest'),
    path('lessons/<int:lesson_id>/progress/', LessonWatchProgressView.as_view(), name='lesson-watch-progress'),
    path('courses/<int:course_id>/quiz/', GetQuizView.as_view(), name='course-quiz'),
    path('courses/<int:course_id>/quiz/check/', CheckQuizView.as_view(), name='course-quiz-check'),

    path('resume/export/', ResumeExportView.as_view(), name='resume-export'),

    path('teacher/courses/', TeacherCourseListView.as_view(), name='teacher-courses'),
    path('teacher/activity/', TeacherActivityView.as_view(), name='teacher-activity'),
    path('teacher/modules/', TeacherModuleListCreateView.as_view(), name='teacher-modules'),
    path('teacher/modules/<int:pk>/', TeacherModuleDetailView.as_view(), name='teacher-module-detail'),
    path('teacher/courses/<int:course_id>/reorder-modules/', ReorderModulesView.as_view(), name='teacher-reorder-modules'),
    path('teacher/courses/<int:course_id>/lessons/', TeacherLessonListCreateView.as_view(), name='teacher-lessons'),
    path('teacher/lessons/', TeacherLessonCreateView.as_view(), name='teacher-lesson-create'),
    path('teacher/lessons/<int:pk>/', TeacherLessonDetailView.as_view(), name='teacher-lesson-detail'),
    path('teacher/modules/<int:module_id>/reorder-lessons/', ReorderLessonsView.as_view(), name='teacher-reorder-lessons'),
    path('teacher/lessons/<int:lesson_id>/quiz-config/', TeacherQuizConfigView.as_view(), name='teacher-quiz-config'),
    path('teacher/courses/<int:course_id>/generate-final-exam/', GenerateFinalExamView.as_view(), name='teacher-generate-final-exam'),
    path('teacher/lessons/<int:lesson_id>/attachments/', TeacherLessonAttachmentListCreateView.as_view(), name='teacher-lesson-attachments'),
    path('teacher/attachments/<int:attachment_id>/', TeacherLessonAttachmentDetailView.as_view(), name='teacher-attachment-detail'),
    path('teacher/upload-image/', TeacherUploadImageView.as_view(), name='teacher-upload-image'),
    path('teacher/lessons/<int:lesson_id>/questions/', TeacherLessonQuestionListCreateView.as_view(), name='teacher-lesson-questions'),
    path('teacher/questions/<int:pk>/', TeacherQuestionDetailView.as_view(), name='teacher-question-detail'),
    path('teacher/courses/<int:pk>/', TeacherCourseDetailView.as_view(), name='teacher-course-detail'),
    path('teacher/courses/<int:course_id>/quiz-editor/', TeacherQuizUpdateView.as_view(), name='teacher-quiz-editor'),

    path('employer/search/', EmployerStudentSearchView.as_view(), name='student-search'),
    path('employer/offer/', EmployerJobOfferView.as_view(), name='send-offer'),
    path('employer/offers/', EmployerOffersListView.as_view(), name='employer-offers'),

    path('student/offers/', StudentJobOffersView.as_view(), name='student-offers'),
    path('notifications/count/', NotificationCountView.as_view(), name='notification-count'),
    path('offers/<int:pk>/update/', JobOfferUpdateView.as_view(), name='offer-update'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
]
