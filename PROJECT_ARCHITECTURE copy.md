# PROJECT_ARCHITECTURE.md

## 1. Общее описание проекта
- Название: ElCourse
- Тип: платформа профессионального обучения с карьерной интеграцией (LMS + HR)
- Целевая аудитория: студенты, преподаватели, работодатели

## 2. Технологический стек
### Бэкенд:
- Django 5.x, Django REST Framework (DRF) — реализовано
- БД: PostgreSQL в продакшене, SQLite для разработки (в репозитории есть db.sqlite3)
- JWT-аутентификация: DRF SimpleJWT (эндпойнты /api/token/ и /api/token/refresh/ настроены). Текущая фронтенд-реализация хранит access/refresh в localStorage (api.js), рекомендуется переход на HttpOnly cookies + refresh-rotation для безопасности
- Celery + Redis — планируемо (не найдено в репозитории)
- Django Channels — опционально (WebSocket), не реализовано

### Фронтенд:
- Vue 3 (Composition API), Vue Router, Pinia
- Tailwind CSS
- Three.js (в компоненте HeroAnimation.vue) — 3D-анимация на главной
- Axios (api.js) с перехватчиком запросов/ответов (добавляет Authorization из localStorage)

### Инфраструктура (планируемая / частичная):
- ASGI: Daphne (рекомендация при реализации Channels)
- FFmpeg + Celery (для конвертации видео в HLS) — план
- Nginx — отдача статики/медиа в проде

## 3. Архитектура базы данных (модели)
На основе backend/platform_app/models.py — основные модели и ключевые поля/связи:

- User (extends AbstractUser)
  - role: CharField(choices=[student, teacher, employer])
  - skills: ManyToManyField('Skill') — навыки пользователя
  - friends: ManyToManyField('self', symmetrical=True) — дружбы
  - avatar: ImageField(upload_to='avatars/')
  - bio: TextField
  - is_verified: BooleanField
  - связи: User ↔ Skill (M2M), User ↔ User (friends)

- Skill
  - name: CharField
  - связи: Skill.courses (ManyToMany from Course)

- Course
  - author: ForeignKey(User, limit_choices_to role='teacher')
  - title, description, image
  - skills_covered: ManyToManyField(Skill)
  - связи: Course → Lesson (one-to-many), Course → Question (one-to-many)

- Lesson
  - course: ForeignKey(Course, related_name='lessons')
  - title, video_url, content, order
  - Meta.ordering = ['order']

- LessonProgress
  - user: ForeignKey(User)
  - lesson: ForeignKey(Lesson)
  - is_completed: Boolean
  - completed_at: DateTime
  - unique_together = (user, lesson)

- ActivityLog
  - user: ForeignKey(User)
  - date: DateField(auto_now_add=True)
  - action_type: CharField (lesson_completed, quiz_passed)
  - count: IntegerField
  - unique_together = (user, date, action_type)

- Question
  - course: ForeignKey(Course)
  - text: TextField

- Choice
  - question: ForeignKey(Question)
  - text: CharField
  - is_correct: BooleanField

- JobOffer
  - employer: ForeignKey(User, related_name='sent_offers')
  - student: ForeignKey(User, related_name='received_offers')
  - message, contact_link, status, created_at
  - is_read_by_student / is_read_by_employer

Замечания:
- Нет явной модели Notification / Chat / Message в models.py — уведомления реализуются частично через статус JobOffer (NotificationCountView подсчитывает непрочитанные офферы).
- Нет отдельной модели UserSkill — используется ManyToMany Skill.

## 4. Структура API (основные эндпоинты)
Файлы: backend/config/urls.py подключает platform_app.urls под префиксом /api/
Основные маршруты (backend/platform_app/urls.py):

- Аутентификация
  - POST /api/token/ → TokenObtainPairView (login, возвращает access+refresh)
  - POST /api/token/refresh/ → TokenRefreshView
  - POST /api/register/ → RegisterView (создание пользователя)

- Профили / пользователи
  - GET/PATCH /api/me/ → UserProfileView (GET возвращает профиль), /api/profile/update/ (PATCH) — обновление bio/avatar
  - GET /api/me/activity/ → UserActivityView (heatmap)
  - GET /api/users/{username}/ → PublicProfileView
  - GET /api/users/{username}/activity/ → PublicUserActivityView
  - POST /api/users/{username}/friend/ → FriendToggleView
  - GET /api/community/ → CommunityView (фильтрация по навыкам / search)

- Курсы / уроки / тесты
  - Router: /api/courses/ (CourseViewSet) — список курсов
  - GET /api/courses/{pk}/ → CourseDetailAPIView
  - GET /api/lessons/{pk}/ → LessonDetailAPIView
  - POST /api/lessons/{lesson_id}/complete/ → CompleteLessonView
  - GET /api/courses/{course_id}/quiz/ → GetQuizView
  - POST /api/courses/{course_id}/quiz/check/ → CheckQuizView
  - /api/skills/ → SkillViewSet (справочник навыков)

- Резюме / экспорт
  - GET /api/resume/export/ → ResumeExportView (генерация PDF через xhtml2pdf)

- Teacher (контент-менеджмент)
  - GET /api/teacher/courses/ → TeacherCourseListView
  - POST/PATCH /api/teacher/courses/{course_id}/lessons/ → TeacherLessonListCreateView
  - GET/PATCH /api/teacher/courses/{pk}/ → TeacherCourseDetailView
  - PATCH /api/teacher/courses/{course_id}/quiz-editor/ → TeacherQuizUpdateView

- Employer / офферы
  - GET /api/employer/search/ → EmployerStudentSearchView
  - POST /api/employer/offer/ → EmployerJobOfferView
  - GET /api/employer/offers/ → EmployerOffersListView
  - GET /api/student/offers/ → StudentJobOffersView
  - PATCH /api/offers/{pk}/update/ → JobOfferUpdateView

- Уведомления
  - GET /api/notifications/count/ → NotificationCountView (подсчёт непрочитанных офферов по роли)

Примечание: нет явного /api/auth/ namespace — simplejwt эндпойнты подключены напрямую.

## 5. Структура фронтенда (ключевые страницы и компоненты)
Файл: frontend/src/router/index.js — основные маршруты:

- HomeView ("/")
  - Компоненты: HeroAnimation.vue (Three.js), карточки курсов
  - Ответственность: показ витрины, загрузка /courses/ и статистики

- LoginView (/login), Register (маршрут /register использует LoginView)
  - Компоненты: форма логина
  - Логика: POST /api/token/ → сохранение access/refresh в localStorage, затем GET /api/me/

- ProfileView (/profile)
  - Компоненты/блоки: header профиля, активити heatmap, Digital Skill Passport
  - Эндпоинты: GET /me/, GET /me/activity/, PATCH /profile/update/, GET /resume/export/

- PublicProfileView (/user/:username)
  - Просмотр публичных данных и активности

- CommunityView (/community)
  - Список пользователей с фильтрацией по навыкам (/api/community/)

- CourseDetailView (/course/:id)
  - Отображает course, список уроков; вызывает /courses/{id}/

- LessonView (/course/:courseId/lesson/:lessonId)
  - Вставка видео (YouTube embed), отображение контента, кнопка "Завершить урок" → POST /lessons/{id}/complete/

- QuizView (/course/:id/quiz)
  - Загрузка вопросов GET /courses/{id}/quiz/, отправка ответов POST /courses/{id}/quiz/check/

- TeacherDashboard (/teacher)
  - Управление курсами: GET /teacher/courses/, POST/PATCH через teacher endpoints; загрузка /skills/ для привязки навыков

- NotificationsView (/notifications)
  - Подсчёт уведомлений через /notifications/count/

Замечания по фронтенду:
- api.js задаёт baseURL = http://127.0.0.1:8000/api и перехватчики (в request добавляет Authorization из localStorage, в response на 401 очищает токены и редиректит на /login).
- В некоторых местах используются прямые axios вызовы с абсолютными URL (http://127.0.0.1:8000), что создаёт дублирование и риск ошибок.
