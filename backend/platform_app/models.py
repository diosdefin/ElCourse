from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    IS_STUDENT = 'student'
    IS_TEACHER = 'teacher'
    IS_EMPLOYER = 'employer'

    ROLE_CHOICES = [
        (IS_STUDENT, 'Студент'),
        (IS_TEACHER, 'Преподаватель'),
        (IS_EMPLOYER, 'Работодатель'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=IS_STUDENT, verbose_name='Роль')
    skills = models.ManyToManyField('Skill', blank=True, related_name='users', verbose_name='Навыки пользователя')
    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    telegram = models.CharField(max_length=255, blank=True, null=True)
    github = models.CharField(max_length=255, blank=True, null=True)
    linkedin = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, verbose_name='О себе')
    is_verified = models.BooleanField(default=False, verbose_name='Верифицирован')


class Skill(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название навыка')

    def __str__(self):
        return self.name


class Course(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, verbose_name='Автор')
    title = models.CharField(max_length=200, verbose_name='Название курса')
    description = models.TextField(verbose_name='Описание')
    image = models.ImageField(upload_to='courses/', blank=True, null=True, verbose_name='Обложка')
    skills_covered = models.ManyToManyField(Skill, related_name='courses', verbose_name='Получаемые навыки')

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class Lesson(models.Model):
    TYPE_VIDEO = 'video'
    TYPE_TEXT = 'text'
    TYPE_QUIZ = 'quiz'
    TYPE_FINAL_EXAM = 'final_exam'

    TYPE_CHOICES = [
        (TYPE_VIDEO, 'Video'),
        (TYPE_TEXT, 'Text'),
        (TYPE_QUIZ, 'Quiz'),
        (TYPE_FINAL_EXAM, 'Final exam'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='Курс')
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, related_name='lessons', null=True, blank=True)
    title = models.CharField(max_length=200, verbose_name='Название урока')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_VIDEO)
    video_url = models.URLField(blank=True, verbose_name='Ссылка на видео')
    content = models.TextField(verbose_name='Текст урока')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядковый номер')
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.module and self.course_id != self.module.course_id:
            self.course = self.module.course
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.course.title} - {self.title}'


def student_visible_lessons_queryset(course):
    return (
        Lesson.objects
        .filter(course=course, is_published=True)
        .order_by('module__order', 'module_id', 'order', 'id')
    )


class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)
    watched_seconds = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    attempts_used = models.PositiveIntegerField(default=0)
    blocked_until = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user.username} - {self.lesson.title} - {"Пройден" if self.is_completed else "В процессе"}'


class LessonVideo(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_PROCESSING, 'Обрабатывается'),
        (STATUS_READY, 'Готово'),
        (STATUS_FAILED, 'Ошибка'),
    ]

    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='video_asset')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    m3u8_url = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.lesson.title} - {self.status}'


class ActivityLog(models.Model):
    ACTION_LESSON_COMPLETED = 'lesson_completed'
    ACTION_QUIZ_PASSED = 'quiz_passed'
    ACTION_COURSE_CREATED = 'course_created'
    ACTION_LESSON_CREATED = 'lesson_created'
    ACTION_VIDEO_UPLOADED = 'video_uploaded'
    ACTION_QUIZ_UPDATED = 'quiz_updated'

    STUDENT_ACTION_TYPES = (
        ACTION_LESSON_COMPLETED,
        ACTION_QUIZ_PASSED,
    )

    TEACHER_ACTION_TYPES = (
        ACTION_COURSE_CREATED,
        ACTION_LESSON_CREATED,
        ACTION_VIDEO_UPLOADED,
        ACTION_QUIZ_UPDATED,
    )

    ACTION_CHOICES = [
        (ACTION_COURSE_CREATED, 'Course created'),
        (ACTION_LESSON_CREATED, 'Lesson created'),
        (ACTION_VIDEO_UPLOADED, 'HLS video uploaded'),
        (ACTION_QUIZ_UPDATED, 'Quiz updated'),
        (ACTION_LESSON_COMPLETED, 'Урок завершен'),
        (ACTION_QUIZ_PASSED, 'Квиз пройден'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    date = models.DateField(auto_now_add=True)
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    count = models.IntegerField(default=1)

    class Meta:
        ordering = ['date', 'action_type']
        unique_together = ('user', 'date', 'action_type')
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'date', 'action_type']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.action_type} ({self.count})'


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions', verbose_name='Курс')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    text = models.TextField(verbose_name='Текст вопроса')
    is_multiple = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f'{self.course.title} - {self.text[:50]}'


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name='Вопрос')
    text = models.CharField(max_length=255, verbose_name='Текст ответа')
    is_correct = models.BooleanField(default=False, verbose_name='Правильный?')

    def __str__(self):
        return self.text


class QuizConfig(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz_config')
    passing_score_percentage = models.IntegerField(default=80)
    max_attempts = models.IntegerField(default=3)
    penalty_hours = models.IntegerField(default=24)
    time_limit_minutes = models.IntegerField(default=0, help_text='0 = без ограничения')

    def __str__(self):
        return f'Quiz config for lesson {self.lesson_id}'


class LessonAttachment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='lesson_attachments/')
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or f'Attachment {self.id}'


class JobOffer(models.Model):
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_offers')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_offers')
    message = models.TextField(blank=True)
    contact_link = models.CharField(max_length=255, blank=True, help_text='Например: https://t.me/employer_hr')
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read_by_student = models.BooleanField(default=False)
    is_read_by_employer = models.BooleanField(default=True)

    def __str__(self):
        return f'Offer from {self.employer.username} to {self.student.username} ({self.status})'



class Vacancy(models.Model):
    FORMAT_REMOTE = 'remote'
    FORMAT_OFFICE = 'office'
    FORMAT_HYBRID = 'hybrid'
    FORMAT_ANY = 'any'

    WORK_FORMAT_CHOICES = [
        (FORMAT_REMOTE, 'Удалённо'),
        (FORMAT_OFFICE, 'В офисе'),
        (FORMAT_HYBRID, 'Гибрид'),
        (FORMAT_ANY, 'Любой формат'),
    ]

    TYPE_FULL_TIME = 'full_time'
    TYPE_PART_TIME = 'part_time'
    TYPE_INTERNSHIP = 'internship'
    TYPE_PROJECT = 'project'

    EMPLOYMENT_TYPE_CHOICES = [
        (TYPE_FULL_TIME, 'Полная занятость'),
        (TYPE_PART_TIME, 'Частичная занятость'),
        (TYPE_INTERNSHIP, 'Стажировка'),
        (TYPE_PROJECT, 'Проектная работа'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликована'),
        (STATUS_CLOSED, 'Закрыта'),
    ]

    employer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vacancies',
        limit_choices_to={'role': User.IS_EMPLOYER},
        verbose_name='Работодатель',
    )
    title = models.CharField(max_length=160, verbose_name='Название вакансии')
    company_name = models.CharField(max_length=160, blank=True, verbose_name='Компания')
    description = models.TextField(max_length=4000, verbose_name='Описание')
    requirements = models.TextField(max_length=3000, blank=True, verbose_name='Требования')
    skills = models.ManyToManyField(Skill, blank=True, related_name='vacancies', verbose_name='Навыки')
    work_format = models.CharField(max_length=20, choices=WORK_FORMAT_CHOICES, default=FORMAT_ANY, verbose_name='Формат работы')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default=TYPE_FULL_TIME, verbose_name='Тип занятости')
    location = models.CharField(max_length=160, blank=True, verbose_name='Локация')
    salary_from = models.PositiveIntegerField(null=True, blank=True, verbose_name='Зарплата от')
    salary_to = models.PositiveIntegerField(null=True, blank=True, verbose_name='Зарплата до')
    contact_link = models.CharField(max_length=255, blank=True, help_text='Например: https://t.me/hr')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['employer', 'status']),
        ]

    def __str__(self):
        return self.title


class VacancyApplication(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_VIEWED = 'viewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Отправлен'),
        (STATUS_VIEWED, 'Просмотрен'),
        (STATUS_ACCEPTED, 'Принят'),
        (STATUS_REJECTED, 'Отклонён'),
        (STATUS_WITHDRAWN, 'Отозван'),
    ]

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacancy_applications')
    message = models.TextField(max_length=1200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_read_by_student = models.BooleanField(default=True)
    is_read_by_employer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('vacancy', 'student')
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['vacancy', 'status']),
            models.Index(fields=['is_read_by_student']),
            models.Index(fields=['is_read_by_employer']),
        ]

    def __str__(self):
        return f'{self.student.username} → {self.vacancy.title} ({self.status})'
