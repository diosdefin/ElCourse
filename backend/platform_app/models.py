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


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='Курс')
    title = models.CharField(max_length=200, verbose_name='Название урока')
    video_url = models.URLField(blank=True, verbose_name='Ссылка на видео')
    content = models.TextField(verbose_name='Текст урока')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядковый номер')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user.username} - {self.lesson.title} - {"Пройден" if self.is_completed else "В процессе"}'


class ActivityLog(models.Model):
    ACTION_LESSON_COMPLETED = 'lesson_completed'
    ACTION_QUIZ_PASSED = 'quiz_passed'

    ACTION_CHOICES = [
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

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.action_type} ({self.count})'


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='questions', verbose_name='Курс')
    text = models.TextField(verbose_name='Текст вопроса')

    def __str__(self):
        return f'{self.course.title} - {self.text[:50]}'


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name='Вопрос')
    text = models.CharField(max_length=255, verbose_name='Текст ответа')
    is_correct = models.BooleanField(default=False, verbose_name='Правильный?')

    def __str__(self):
        return self.text


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
