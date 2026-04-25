from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ActivityLog, Course, Lesson, LessonProgress, Skill, User
from .models import Question, Choice

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3 # Сразу показывает 3 пустых поля для ответов

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_filter = ['course']
    
class CustomUserAdmin(UserAdmin):
    # Исправлено: заменяем 'skill' на 'skills' (как в модели)
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'is_verified', 'avatar', 'bio', 'skills', 'friends')}),
    )
    
    # Исправлено: заменяем 'skill' на 'skills'
    filter_horizontal = ('skills', 'friends')
    
    list_display = ('username', 'email', 'role', 'is_staff', 'is_verified')
    list_filter = ('role', 'is_staff', 'is_verified')

# Регистрируем модель User
admin.site.register(User, CustomUserAdmin)

# Остальные модели
admin.site.register(Course)
admin.site.register(Skill)
admin.site.register(Lesson)
admin.site.register(LessonProgress)
admin.site.register(ActivityLog)
