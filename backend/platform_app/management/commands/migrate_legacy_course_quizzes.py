from django.core.management.base import BaseCommand
from django.db import transaction

from platform_app.models import Course, Lesson, Module, Question, QuizConfig


class Command(BaseCommand):
    help = 'Move legacy course-level quiz questions to lesson-level quiz lessons.'

    @transaction.atomic
    def handle(self, *args, **options):
        courses = Course.objects.all().order_by('id')
        migrated_courses = 0
        migrated_questions = 0

        for course in courses:
            legacy_questions = Question.objects.filter(course=course, lesson__isnull=True).order_by('id')
            if not legacy_questions.exists():
                continue

            first_module = Module.objects.filter(course=course).order_by('order', 'id').first()
            if not first_module:
                first_module = Module.objects.create(
                    course=course,
                    title='Legacy module',
                    order=0,
                )

            quiz_lesson = (
                Lesson.objects
                .filter(course=course, module=first_module, type=Lesson.TYPE_QUIZ)
                .order_by('order', 'id')
                .first()
            )

            if not quiz_lesson:
                next_order = Lesson.objects.filter(module=first_module).count()
                quiz_lesson = Lesson.objects.create(
                    course=course,
                    module=first_module,
                    title='Course Quiz',
                    type=Lesson.TYPE_QUIZ,
                    order=next_order,
                    content='',
                    is_published=True,
                )

            question_count = legacy_questions.count()
            legacy_questions.update(lesson=quiz_lesson)
            QuizConfig.objects.get_or_create(lesson=quiz_lesson)

            migrated_courses += 1
            migrated_questions += question_count
            self.stdout.write(
                self.style.WARNING(
                    f'Course {course.id}: moved {question_count} question(s) to lesson {quiz_lesson.id}.'
                )
            )

        self.stdout.write(self.style.SUCCESS(
            f'Legacy migration finished. Courses: {migrated_courses}, Questions: {migrated_questions}.'
        ))
