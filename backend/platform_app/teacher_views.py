from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, Choice, Course, Lesson, LessonAttachment, LessonProgress, Module, Question, QuizConfig, User
from .serializers import (
    CourseSerializer,
    LessonAttachmentSerializer,
    LessonSerializer,
    ModuleSerializer,
    QuestionSerializer,
    QuizConfigSerializer,
    TeacherQuestionSerializer,
)
from .views import record_daily_activity


class TeacherModuleListCreateView(generics.ListCreateAPIView):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.request.query_params.get('course_id')
        queryset = Module.objects.filter(course__author=self.request.user)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset.order_by('order', 'id')

    def perform_create(self, serializer):
        course_id = self.request.data.get('course_id')
        course = get_object_or_404(Course, id=course_id, author=self.request.user)
        next_order = Module.objects.filter(course=course).count()
        order = self.request.data.get('order')
        serializer.save(course=course, order=order if order is not None else next_order)


class TeacherModuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Module.objects.filter(course__author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            Lesson.objects.filter(module=instance).delete()
            self.perform_destroy(instance)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ReorderModulesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id, author=request.user)
        module_ids = request.data.get('module_ids', [])

        for index, module_id in enumerate(module_ids):
            Module.objects.filter(id=module_id, course=course).update(order=index)

        return Response({'status': 'ok'})


class TeacherLessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        module_id = self.request.query_params.get('module_id')
        queryset = Lesson.objects.filter(course_id=course_id, course__author=self.request.user)
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        return queryset.order_by('order', 'id')

    def perform_create(self, serializer):
        course = get_object_or_404(Course, id=self.kwargs['course_id'], author=self.request.user)
        module = None
        module_id = self.request.data.get('module_id') or self.request.data.get('module')
        if module_id:
            module = get_object_or_404(Module, id=module_id, course=course)

        if module:
            next_order = Lesson.objects.filter(module=module).count()
        else:
            next_order = Lesson.objects.filter(course=course, module__isnull=True).count()

        order = self.request.data.get('order')
        lesson = serializer.save(
            course=course,
            module=module,
            order=order if order is not None else next_order,
        )
        record_daily_activity(self.request.user, ActivityLog.ACTION_LESSON_CREATED)

        if lesson.type == Lesson.TYPE_QUIZ and not hasattr(lesson, 'quiz_config'):
            QuizConfig.objects.create(lesson=lesson)


class TeacherLessonCreateView(generics.CreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        module_id = request.data.get('module_id') or request.data.get('module')
        module = get_object_or_404(Module, id=module_id, course__author=request.user)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        next_order = Lesson.objects.filter(module=module).count()
        lesson = serializer.save(
            module=module,
            course=module.course,
            order=request.data.get('order') if request.data.get('order') is not None else next_order,
        )
        record_daily_activity(request.user, ActivityLog.ACTION_LESSON_CREATED)

        if lesson.type == Lesson.TYPE_QUIZ and not hasattr(lesson, 'quiz_config'):
            QuizConfig.objects.create(lesson=lesson)

        return Response(self.get_serializer(lesson).data, status=status.HTTP_201_CREATED)


class TeacherLessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Lesson.objects.filter(course__author=self.request.user)

    def perform_update(self, serializer):
        lesson = serializer.instance
        validated = serializer.validated_data

        if 'module' in validated and validated['module'] and validated['module'].course.author_id != self.request.user.id:
            raise PermissionDenied('Cannot move lesson to a module outside your course.')

        updated_lesson = serializer.save()

        if updated_lesson.type == Lesson.TYPE_QUIZ and not hasattr(updated_lesson, 'quiz_config'):
            QuizConfig.objects.create(lesson=updated_lesson)

        if updated_lesson.type in {Lesson.TYPE_QUIZ, Lesson.TYPE_FINAL_EXAM}:
            record_daily_activity(self.request.user, ActivityLog.ACTION_QUIZ_UPDATED)


class ReorderLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, module_id):
        module = get_object_or_404(Module, id=module_id, course__author=request.user)
        lesson_ids = request.data.get('lesson_ids', [])

        for index, lesson_id in enumerate(lesson_ids):
            Lesson.objects.filter(id=lesson_id, module=module).update(order=index)

        return Response({'status': 'ok'})


class TeacherQuizConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id, course__author=request.user)
        config, _ = QuizConfig.objects.get_or_create(lesson=lesson)
        return Response(QuizConfigSerializer(config).data)

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id, course__author=request.user)
        config, _ = QuizConfig.objects.update_or_create(
            lesson=lesson,
            defaults={
                'passing_score_percentage': request.data.get('passing_score_percentage', 80),
                'max_attempts': request.data.get('max_attempts', 3),
                'penalty_hours': request.data.get('penalty_hours', 24),
                'time_limit_minutes': request.data.get('time_limit_minutes', 0),
            },
        )
        return Response(QuizConfigSerializer(config).data)


class GenerateFinalExamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id, author=request.user)
        source_questions = (
            Question.objects
            .filter(lesson__course=course, lesson__type=Lesson.TYPE_QUIZ)
            .prefetch_related('choices')
            .distinct()
        )

        if not source_questions.exists():
            return Response({'error': 'No quiz questions found in this course.'}, status=status.HTTP_400_BAD_REQUEST)

        final_module, _ = Module.objects.get_or_create(
            course=course,
            title='Final Exam',
            defaults={'order': 999},
        )

        exam_lesson = Lesson.objects.create(
            module=final_module,
            course=course,
            title='Final Exam',
            type=Lesson.TYPE_FINAL_EXAM,
            order=0,
            content='',
            is_published=False,
        )

        for source in source_questions:
            cloned = Question.objects.create(
                course=course,
                lesson=exam_lesson,
                text=source.text,
                is_multiple=source.is_multiple,
                explanation=source.explanation,
            )
            for choice in source.choices.all():
                Choice.objects.create(
                    question=cloned,
                    text=choice.text,
                    is_correct=choice.is_correct,
                )

        QuizConfig.objects.get_or_create(
            lesson=exam_lesson,
            defaults={
                'passing_score_percentage': 80,
                'max_attempts': 3,
                'penalty_hours': 24,
                'time_limit_minutes': 0,
            },
        )

        record_daily_activity(request.user, ActivityLog.ACTION_QUIZ_UPDATED)
        return Response({'message': 'Final exam created', 'lesson_id': exam_lesson.id})


class TeacherLessonAttachmentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id, course__author=request.user)
        serializer = LessonAttachmentSerializer(lesson.attachments.all(), many=True)
        return Response(serializer.data)

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id, course__author=request.user)
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'File is required.'}, status=status.HTTP_400_BAD_REQUEST)

        attachment = LessonAttachment.objects.create(lesson=lesson, file=upload)
        return Response(LessonAttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED)


class TeacherLessonAttachmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, attachment_id):
        attachment = get_object_or_404(LessonAttachment, id=attachment_id, lesson__course__author=request.user)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherUploadImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != User.IS_TEACHER and not request.user.is_staff:
            return Response({'detail': 'Доступ только для преподавателей.'}, status=status.HTTP_403_FORBIDDEN)

        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'Image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = Path(settings.MEDIA_ROOT) / 'content_images'
        upload_dir.mkdir(parents=True, exist_ok=True)

        storage = FileSystemStorage(location=str(upload_dir), base_url=f'{settings.MEDIA_URL}content_images/')
        name = storage.save(image.name, image)
        return Response({'url': storage.url(name)})


class TeacherLessonQuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = TeacherQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lesson_id = self.kwargs['lesson_id']
        return Question.objects.filter(lesson_id=lesson_id, lesson__course__author=self.request.user).prefetch_related('choices')

    def perform_create(self, serializer):
        lesson = get_object_or_404(Lesson, id=self.kwargs['lesson_id'], course__author=self.request.user)
        serializer.save(lesson=lesson, course=lesson.course)
        record_daily_activity(self.request.user, ActivityLog.ACTION_QUIZ_UPDATED)


class TeacherQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TeacherQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Question.objects
            .filter(
                Q(lesson__course__author=self.request.user)
                | Q(lesson__isnull=True, course__author=self.request.user)
            )
            .prefetch_related('choices')
        )


class TeacherQuizUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        # Legacy course-level quiz editor: only questions not attached to lessons.
        questions = Question.objects.filter(course_id=course_id, course__author=request.user, lesson__isnull=True)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id, author=request.user)
        data = request.data

        question = Question.objects.create(
            course=course,
            text=data.get('text', ''),
            is_multiple=bool(data.get('is_multiple', False)),
            explanation=data.get('explanation', ''),
        )

        for choice_data in data.get('choices', []):
            Choice.objects.create(
                question=question,
                text=choice_data.get('text', ''),
                is_correct=bool(choice_data.get('is_correct', False)),
            )

        record_daily_activity(request.user, ActivityLog.ACTION_QUIZ_UPDATED)
        return Response({'message': 'Question created', 'question_id': question.id}, status=status.HTTP_201_CREATED)


class TeacherAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.IS_TEACHER and not request.user.is_staff:
            return Response({'detail': 'Доступ только для преподавателей.'}, status=status.HTTP_403_FORBIDDEN)

        courses = (
            Course.objects
            .filter(author=request.user)
            .prefetch_related('skills_covered', 'modules', 'lessons')
            .order_by('title')
        )
        course_ids = [course.id for course in courses]
        lessons = Lesson.objects.filter(course_id__in=course_ids)
        progress_rows = (
            LessonProgress.objects
            .filter(lesson__course_id__in=course_ids)
            .select_related('user', 'lesson', 'lesson__course')
            .order_by('lesson__course__title', 'user__username')
        )

        distinct_students = set(progress_rows.values_list('user_id', flat=True))
        skill_ids = set()
        for course in courses:
            for skill in course.skills_covered.all():
                skill_ids.add(skill.id)

        lesson_type_counts = {
            'text': lessons.filter(type=Lesson.TYPE_TEXT).count(),
            'video': lessons.filter(type=Lesson.TYPE_VIDEO).count(),
            'quiz': lessons.filter(type=Lesson.TYPE_QUIZ).count(),
            'final_exam': lessons.filter(type=Lesson.TYPE_FINAL_EXAM).count(),
        }

        course_rows = []
        for course in courses:
            course_lessons = list(course.lessons.all())
            total_lessons = len(course_lessons)
            course_progress = [row for row in progress_rows if row.lesson.course_id == course.id]
            course_student_ids = sorted({row.user_id for row in course_progress})

            student_progress_values = []
            for student_id in course_student_ids:
                completed_count = sum(1 for row in course_progress if row.user_id == student_id and row.is_completed)
                student_progress_values.append(int((completed_count / total_lessons) * 100) if total_lessons else 0)

            average_progress = int(sum(student_progress_values) / len(student_progress_values)) if student_progress_values else 0
            average_score_rows = [row.score for row in course_progress if row.score is not None and row.score > 0]
            average_score = int(sum(average_score_rows) / len(average_score_rows)) if average_score_rows else 0
            last_activity_values = [row.completed_at for row in course_progress if row.completed_at]
            last_activity = max(last_activity_values) if last_activity_values else None

            course_rows.append({
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'image': course.image.url if course.image else None,
                'skills': [{'id': skill.id, 'name': skill.name} for skill in course.skills_covered.all()],
                'module_count': course.modules.count(),
                'lesson_count': total_lessons,
                'published_lesson_count': sum(1 for lesson in course_lessons if lesson.is_published),
                'text_lesson_count': sum(1 for lesson in course_lessons if lesson.type == Lesson.TYPE_TEXT),
                'video_lesson_count': sum(1 for lesson in course_lessons if lesson.type == Lesson.TYPE_VIDEO),
                'quiz_lesson_count': sum(1 for lesson in course_lessons if lesson.type == Lesson.TYPE_QUIZ),
                'final_exam_count': sum(1 for lesson in course_lessons if lesson.type == Lesson.TYPE_FINAL_EXAM),
                'student_count': len(course_student_ids),
                'completed_lesson_count': sum(1 for row in course_progress if row.is_completed),
                'average_progress': average_progress,
                'average_score': average_score,
                'last_activity': last_activity,
            })

        student_map = {}
        for row in progress_rows:
            key = (row.lesson.course_id, row.user_id)
            item = student_map.setdefault(key, {
                'student_id': row.user_id,
                'username': row.user.username,
                'email': row.user.email,
                'avatar': row.user.avatar.url if row.user.avatar else None,
                'course_id': row.lesson.course_id,
                'course_title': row.lesson.course.title,
                'total_lessons': 0,
                'completed_lessons': 0,
                'attempts_used': 0,
                'scores': [],
                'last_activity': row.completed_at,
            })
            item['attempts_used'] += row.attempts_used or 0
            if row.score is not None and row.score > 0:
                item['scores'].append(row.score)
            if row.completed_at and (item['last_activity'] is None or row.completed_at > item['last_activity']):
                item['last_activity'] = row.completed_at
            if row.is_completed:
                item['completed_lessons'] += 1

        lessons_count_by_course = {course.id: course.lessons.count() for course in courses}
        student_rows = []
        for item in student_map.values():
            total_lessons = lessons_count_by_course.get(item['course_id'], 0)
            item['total_lessons'] = total_lessons
            item['progress_percentage'] = int((item['completed_lessons'] / total_lessons) * 100) if total_lessons else 0
            item['average_score'] = int(sum(item['scores']) / len(item['scores'])) if item['scores'] else 0
            item.pop('scores', None)
            student_rows.append(item)

        student_rows.sort(key=lambda item: (item['course_title'], -item['progress_percentage'], item['username']))

        activity_rows = (
            ActivityLog.objects
            .filter(user=request.user, action_type__in=ActivityLog.TEACHER_ACTION_TYPES)
            .values('date')
            .annotate(count=Sum('count'))
            .order_by('date')
        )

        return Response({
            'summary': {
                'total_courses': len(course_ids),
                'total_modules': Module.objects.filter(course_id__in=course_ids).count(),
                'total_lessons': lessons.count(),
                'published_lessons': lessons.filter(is_published=True).count(),
                'skills_count': len(skill_ids),
                'students_count': len(distinct_students),
                'completed_lessons': progress_rows.filter(is_completed=True).count(),
                'average_score': int(progress_rows.filter(score__gt=0).aggregate(value=Avg('score'))['value'] or 0),
                'lesson_type_counts': lesson_type_counts,
            },
            'courses': course_rows,
            'students': student_rows,
            'activity': list(activity_rows),
        })


class TeacherCourseListView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'teacher':
            raise PermissionDenied('Teacher role is required')
        return Course.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != 'teacher':
            raise PermissionDenied('Teacher role is required')

        course = serializer.save(author=self.request.user)
        record_daily_activity(self.request.user, ActivityLog.ACTION_COURSE_CREATED)

        skills = self.request.data.getlist('skills_covered')
        if skills:
            course.skills_covered.set(skills)


class TeacherCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(author=self.request.user)

    def perform_update(self, serializer):
        course = serializer.save()

        if 'skills_covered' in self.request.data:
            skills = self.request.data.getlist('skills_covered')
            course.skills_covered.set(skills)
