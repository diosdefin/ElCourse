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

## 6. Ключевые алгоритмы и бизнес-логика
1. JWT-аутентификация
   - Frontend: POST /api/token/ сохраняет access и refresh в localStorage; api.js добавляет Authorization: Bearer <access>.
   - Нет автоматического механизма refresh-token в api.js (только очистка при 401).
2. Генерация PDF-резюме
   - ResumeExportView использует xhtml2pdf (pisa) + HTML-шаблон (resume_template.html) и встраивание шрифта в base64.
3. Система «цифрового паспорта навыков»
   - После успешного прохождения Quiz (CheckQuizView) проверяется доля правильных ответов >= 80% → новые навыки из course.skills_covered добавляются в user.skills.
   - LessonProgress + ActivityLog используются для расчёта прогресса и heatmap активности.
4. 3D-анимация на главной
   - HeroAnimation.vue использует Three.js + GLTFLoader для модели phoenix.glb; есть автоповорот, drag interaction и анимационные клипы.
5. Видео/чат
   - Видео: LessonView поддерживает YouTube embed; HLS-пайплайн отсутствует (планируется FFmpeg + Celery для конвертации).
   - Чат/Message: не реализованы (рекомендация — начать с поллинга, затем WebSocket/Channels)

## 7. Оценка текущего состояния проекта (в процентах)
- Авторизация и роли: 85% (SimpleJWT настроен, frontend сохраняет токены в localStorage)
- Профили и навыки: 80% (CRUD профиля, M2M Skills, Passport реализованы)
- Система друзей / сообщество: 60% (FriendToggle и CommunityView есть, UI покрытие частично)
- CRUD курсов и уроков: 80% (Teacher endpoints + frontend редакторы)
- Загрузка и воспроизведение видео (обычное): 70% (YouTube embed поддержан)
- Тесты и сохранение результатов: 75% (Quiz/Check реализованы, добавление навыков есть)
- Поиск людей по навыкам: 70% (CommunityView с фильтрацией)
- UI/UX (адаптив, лоадеры, обработка ошибок): 75%
- Безопасность и производительность (с учётом доработок): 60% (требуется миграция на HttpOnly cookies/refresh, CSRF/secure flags, оптимизация запросов)
- Чат / личные сообщения: 0% (не реализовано)

Общая оценка готовности: 65–70%.

## 8. Что осталось сделать (по приоритетам)
1. HLS-видео (адаптивный стриминг) – высокая сложность: FFmpeg + Celery pipeline, хранение сегментов, hls.js на фронте
2. Регистрация и UX потока регистрации (/register) — низкая сложность (маршрут есть, фронтенд/логика форм доработать)
3. Настройки профиля (редактирование bio, контактов, аватара) — низкая
4. Пагинация и оптимизация запросов (N+1, select_related/prefetch_related) — низкая
5. Чат (поллинг как MVP, потом WebSocket через Channels/Daphne) — средняя
6. Доработка тестов (юнит/интеграционные тесты для ключевых вьюшек) — средняя
7. Дашборды (аналитика для преподавателя/работодателя) — средняя
8. Полировка UI/UX (лоадеры, ошибки, мобильная адаптация) — низкая

## 9. Технические рекомендации для дальнейшей разработки
- Аутентификация
  - Перейти на HttpOnly, Secure cookies для refresh токена + rotation; хранить access в памяти/Pinia и рефрешить автоматически в interceptor.
  - Добавить CSRF защиту при использовании cookie-based auth.
- HLS и видео
  - Использовать Celery + Redis для фоновой конвертации видео в HLS (FFmpeg), хранить сегменты и .m3u8; фронтенд — hls.js
- Чат
  - MVP: polling/long-polling (ниская сложность). Для real-time: Django Channels + Daphne + фронтенд WebSocket
- Дашборды
  - Агрегирующие эндпоинты в DRF, визуализация — Chart.js или ECharts
- Производительность
  - Применять select_related/prefetch_related в критичных эндпоинтах; кэшировать частые запросы
- CI / тестирование
  - Добавить тесты на ключевые эндпоинты и сценарии (регистрация, прохождение квиза, завершение урока)
- Безопасность
  - Перенести токены из localStorage, реализовать refresh flow, включить HTTPS и HSTS в продакшене

## 10. Заключение
Проект имеет чёткую и разумную архитектуру: модели и API покрывают основной функционал LMS + HR (курсы, квизы, цифровой паспорт навыков, офферы). Для полноценного первого релиза нужна доработка видео-пайплайна и базового чата, а также усиление безопасности (аутентификация/токены). Оценочный объём оставшихся работ: ~30–40 часов.

---

Если нужно, могу:
- добавить краткий roadmap (поштучный план задач с приоритетами),
- создать TODOs в session SQL таблице,
- или начать реализацию конкретной задачи (например: миграция токенов на HttpOnly cookies или настроить Celery + FFmpeg).