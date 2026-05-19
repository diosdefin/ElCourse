import base64
import os
from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.db.models import F, Q, Sum
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count

try:
    from xhtml2pdf import pisa
except ImportError:  # pragma: no cover - depends on local optional dependency
    pisa = None

from .models import (
    ActivityLog,
    Choice,
    Course,
    JobOffer,
    Lesson,
    LessonAttachment,
    LessonProgress,
    LessonVideo,
    Module,
    Question,
    QuizConfig,
    Skill,
    User,
    Vacancy,
    VacancyApplication,
    student_visible_lessons_queryset,
)
from .serializers import (
    ActivityDaySerializer,
    CourseOutlineSerializer,
    CommunityUserSerializer,
    CourseSerializer,
    JobOfferSerializer,
    LessonProgressSecondsSerializer,
    StudentAttachmentSerializer,
    StudentOutlineLessonSerializer,
    StudentQuizQuestionSerializer,
    LessonSerializer,
    LessonVideoSerializer,
    PublicProfileSerializer,
    RegisterSerializer,
    SkillSerializer,
    UserSettingsSerializer,
    UserProfileSerializer,
    VacancyApplicationSerializer,
    VacancySerializer,
)
from .tasks import convert_to_hls


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 30


MAX_DAILY_ACTIVITY_COUNT = 10


def record_daily_activity(user, action_type):
    today = timezone.localdate()
    activity, created = ActivityLog.objects.get_or_create(
        user=user,
        date=today,
        action_type=action_type,
        defaults={'count': 1},
    )
    if not created:
        ActivityLog.objects.filter(pk=activity.pk, count__lt=MAX_DAILY_ACTIVITY_COUNT).update(
            count=F('count') + 1
        )
        activity.refresh_from_db(fields=['count'])
    return activity


def get_yearly_activity_queryset(user, year, action_types=None):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    queryset = ActivityLog.objects.filter(user=user, date__range=(start_date, end_date))
    if action_types:
        queryset = queryset.filter(action_type__in=action_types)
    return queryset.values('date').annotate(count=Sum('count')).order_by('date')


def get_activity_year(request, default_year=None):
    requested_year = request.query_params.get('year')
    if requested_year is None:
        return default_year or timezone.localdate().year

    try:
        return int(requested_year)
    except (TypeError, ValueError):
        return None


def _student_visible_lessons(course):
    return (
        student_visible_lessons_queryset(course)
        .select_related('module')
        .prefetch_related('attachments')
    )


def _student_locked_lesson_ids(visible_lessons, progress_map):
    locked_ids = set()
    previous_completed = True

    for lesson in visible_lessons:
        is_completed = bool(progress_map.get(lesson.id) and progress_map[lesson.id].is_completed)
        if not previous_completed:
            locked_ids.add(lesson.id)
        if not is_completed:
            previous_completed = False

    return locked_ids


def _student_can_access_lesson(student, lesson):
    if not lesson.is_published:
        return False

    visible_lessons = list(student_visible_lessons_queryset(lesson.course).only('id'))
    progress_map = {
        row.lesson_id: row
        for row in LessonProgress.objects.filter(user=student, lesson__in=visible_lessons)
    }
    locked_ids = _student_locked_lesson_ids(visible_lessons, progress_map)
    return lesson.id not in locked_ids


def _user_can_access_lesson_resource(user, lesson):
    if user.is_staff:
        return True
    if user.role == User.IS_STUDENT:
        return lesson.is_published and _student_can_access_lesson(user, lesson)
    if user.role == User.IS_TEACHER:
        return lesson.course.author_id == user.id
    return False


class ResumeExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if pisa is None:
            return HttpResponse('Генерация PDF временно недоступна: библиотека xhtml2pdf не установлена.', status=503)

        user = request.user
        target_user = user
        requested_user_id = request.query_params.get('user_id')

        if requested_user_id:
            if str(user.id) == requested_user_id:
                target_user = user
            elif user.role == User.IS_EMPLOYER or user.is_staff:
                try:
                    target_user = User.objects.prefetch_related('skills').get(id=requested_user_id, role=User.IS_STUDENT)
                except User.DoesNotExist:
                    return HttpResponse('Студент для резюме не найден', status=404)
            else:
                return HttpResponse('Недостаточно прав для скачивания чужого резюме', status=403)

        font_path = os.path.join(settings.BASE_DIR, 'fonts', 'Roboto-Regular.ttf')
        try:
            with open(font_path, 'rb') as font_file:
                font_data = base64.b64encode(font_file.read()).decode('utf-8')
        except Exception as exc:
            return HttpResponse(f'Ошибка чтения шрифта: {exc}', status=500)

        context = {
            'username': target_user.username,
            'email': target_user.email,
            'bio': target_user.bio,
            'skills': target_user.skills.all(),
            'font_base64': font_data,
        }

        template = get_template('resume_template.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Resume_{target_user.username}.pdf"'

        pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')
        if pisa_status.err:
            return HttpResponse('Ошибка генерации PDF', status=500)
        return response


class CompleteLessonView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        user = request.user
        if user.role != User.IS_STUDENT:
            return Response({'error': 'Только студенты могут завершать уроки'}, status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if not _student_can_access_lesson(user, lesson):
            return Response({'error': 'Урок пока недоступен.'}, status=status.HTTP_403_FORBIDDEN)
        progress, created = LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
            defaults={'is_completed': True},
        )

        newly_completed = False
        if created:
            newly_completed = True
        elif not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save(update_fields=['is_completed', 'completed_at'])
            newly_completed = True

        if newly_completed:
            record_daily_activity(user, ActivityLog.ACTION_LESSON_COMPLETED)

        visible_lesson_ids = list(
            student_visible_lessons_queryset(lesson.course).values_list('id', flat=True)
        )
        total_lessons = len(visible_lesson_ids)
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson_id__in=visible_lesson_ids,
            is_completed=True,
        ).count()
        progress_percentage = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        return Response({
            'is_completed': True,
            'already_completed': not newly_completed,
            'course_completed': total_lessons > 0 and completed_lessons == total_lessons,
            'course_progress_percentage': progress_percentage,
        })


class LessonVideoUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course__author'), id=lesson_id)

        if request.user.role != User.IS_TEACHER and not request.user.is_staff:
            return Response({'detail': 'Только преподаватели могут загружать видео.'}, status=status.HTTP_403_FORBIDDEN)

        if not request.user.is_staff and lesson.course.author_id != request.user.id:
            return Response({'detail': 'Нельзя загружать видео в чужой урок.'}, status=status.HTTP_403_FORBIDDEN)

        uploaded_file = request.FILES.get('video')
        if not uploaded_file:
            return Response({'detail': 'Файл video обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads' / f'lesson_{lesson.id}'
        upload_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(uploaded_file.name).suffix or '.mp4'
        source_path = upload_dir / f'source{extension}'

        with source_path.open('wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        video_asset, _ = LessonVideo.objects.get_or_create(lesson=lesson)
        video_asset.status = LessonVideo.STATUS_PENDING
        video_asset.m3u8_url = ''
        video_asset.error_message = ''
        video_asset.save(update_fields=['status', 'm3u8_url', 'error_message', 'updated_at'])
        if request.user.role == User.IS_TEACHER:
            record_daily_activity(request.user, ActivityLog.ACTION_VIDEO_UPLOADED)

        task = convert_to_hls.delay(lesson.id, str(source_path))

        return Response(
            {
                'status': video_asset.status,
                'task_id': task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class LessonVideoManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if not _user_can_access_lesson_resource(request.user, lesson):
            return Response({'detail': 'Недостаточно прав для просмотра видео этого урока.'}, status=status.HTTP_403_FORBIDDEN)

        video_asset, _ = LessonVideo.objects.get_or_create(lesson=lesson)
        payload = LessonVideoSerializer(video_asset).data

        manifest_url = payload.get('m3u8_url')
        if manifest_url:
            payload['m3u8_url'] = request.build_absolute_uri(manifest_url)

        return Response(payload)


class LessonWatchProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if not _user_can_access_lesson_resource(request.user, lesson):
            return Response({'detail': 'Lesson progress is not available for this lesson.'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Только студенты могут получать прогресс просмотра.'}, status=status.HTTP_403_FORBIDDEN)

        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        return Response({
            'watched_seconds': progress.watched_seconds,
            'is_completed': progress.is_completed,
        })

    def patch(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if not _user_can_access_lesson_resource(request.user, lesson):
            return Response({'detail': 'Lesson progress is not available for this lesson.'}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Только студенты могут обновлять прогресс просмотра.'}, status=status.HTTP_403_FORBIDDEN)

        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        raw_seconds = request.data.get('watched_seconds', 0)
        try:
            watched_seconds = int(float(raw_seconds))
        except (TypeError, ValueError):
            return Response({'detail': 'watched_seconds должен быть числом.'}, status=status.HTTP_400_BAD_REQUEST)

        watched_seconds = max(0, watched_seconds)
        if watched_seconds > progress.watched_seconds:
            progress.watched_seconds = watched_seconds
            progress.save(update_fields=['watched_seconds'])

        return Response(LessonProgressSecondsSerializer(progress).data)


class CourseOutlineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

        if request.user.role == User.IS_STUDENT:
            visible_lessons = list(_student_visible_lessons(course))
            progress_rows = LessonProgress.objects.filter(user=request.user, lesson__in=visible_lessons)
            progress_map = {row.lesson_id: row for row in progress_rows}
            locked_ids = _student_locked_lesson_ids(visible_lessons, progress_map)
        elif request.user.is_staff or (request.user.role == User.IS_TEACHER and course.author_id == request.user.id):
            visible_lessons = list(
                Lesson.objects
                .filter(course=course)
                .select_related('module')
                .prefetch_related('attachments')
                .order_by('module__order', 'module_id', 'order', 'id')
            )
            progress_map = {}
            locked_ids = set()
        else:
            return Response({'detail': 'Недостаточно прав для просмотра курса.'}, status=status.HTTP_403_FORBIDDEN)

        modules = list(Module.objects.filter(course=course).order_by('order', 'id'))
        lessons_by_module = {module.id: [] for module in modules}
        orphan_lessons = []

        for lesson in visible_lessons:
            if lesson.module_id and lesson.module_id in lessons_by_module:
                lessons_by_module[lesson.module_id].append(lesson)
            else:
                orphan_lessons.append(lesson)

        visible_modules = []
        for module in modules:
            module_lessons = lessons_by_module[module.id]
            if module_lessons:
                module._visible_lessons = module_lessons
                visible_modules.append(module)

        course._visible_modules = visible_modules
        serializer = CourseOutlineSerializer(
            course,
            context={
                'request': request,
                'progress_map': progress_map,
                'locked_lesson_ids': locked_ids,
            },
        )
        payload = serializer.data

        if orphan_lessons:
            orphan_serializer = StudentOutlineLessonSerializer(
                orphan_lessons,
                many=True,
                context={
                    'request': request,
                    'progress_map': progress_map,
                    'locked_lesson_ids': locked_ids,
                },
            )
            payload['modules'].append({
                'id': 0,
                'title': 'Без модуля',
                'order': 9999,
                'lessons': orphan_serializer.data,
            })

        return Response(payload)


class StudentLessonAttachmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)

        if request.user.role == User.IS_STUDENT:
            if not _student_can_access_lesson(request.user, lesson):
                return Response({'detail': 'Урок пока недоступен.'}, status=status.HTTP_403_FORBIDDEN)
        elif not (request.user.is_staff or (request.user.role == User.IS_TEACHER and lesson.course.author_id == request.user.id)):
            return Response({'detail': 'Недостаточно прав.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = StudentAttachmentSerializer(lesson.attachments.all(), many=True, context={'request': request})
        return Response(serializer.data)


class LessonQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if lesson.type not in {Lesson.TYPE_QUIZ, Lesson.TYPE_FINAL_EXAM}:
            return Response({'detail': 'Этот урок не является тестом.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.role == User.IS_STUDENT:
            if not _student_can_access_lesson(request.user, lesson):
                return Response({'detail': 'Урок пока недоступен.'}, status=status.HTTP_403_FORBIDDEN)
            progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        elif request.user.is_staff or (request.user.role == User.IS_TEACHER and lesson.course.author_id == request.user.id):
            progress = None
        else:
            return Response({'detail': 'Недостаточно прав.'}, status=status.HTTP_403_FORBIDDEN)

        config, _ = QuizConfig.objects.get_or_create(lesson=lesson)
        questions = Question.objects.filter(lesson=lesson).prefetch_related('choices').order_by('id')
        blocked_until = progress.blocked_until if progress else None

        return Response({
            'lesson_id': lesson.id,
            'lesson_type': lesson.type,
            'quiz_config': {
                'passing_score_percentage': config.passing_score_percentage,
                'max_attempts': config.max_attempts,
                'penalty_hours': config.penalty_hours,
                'time_limit_minutes': config.time_limit_minutes,
            },
            'attempts_used': progress.attempts_used if progress else 0,
            'blocked_until': blocked_until,
            'questions': StudentQuizQuestionSerializer(questions, many=True).data,
        })


class LessonQuizSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        if request.user.role != User.IS_STUDENT:
            return Response({'detail': 'Только студенты могут сдавать тест.'}, status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
        if lesson.type not in {Lesson.TYPE_QUIZ, Lesson.TYPE_FINAL_EXAM}:
            return Response({'detail': 'Этот урок не является тестом.'}, status=status.HTTP_400_BAD_REQUEST)

        if not _student_can_access_lesson(request.user, lesson):
            return Response({'detail': 'Урок пока недоступен.'}, status=status.HTTP_403_FORBIDDEN)

        submitted_answers = request.data.get('answers', {})
        if not isinstance(submitted_answers, dict):
            return Response({'detail': 'Поле answers должно быть объектом.'}, status=status.HTTP_400_BAD_REQUEST)

        questions = list(Question.objects.filter(lesson=lesson).prefetch_related('choices').order_by('id'))
        if not questions:
            return Response({'detail': 'Для этого урока нет вопросов.'}, status=status.HTTP_400_BAD_REQUEST)

        config, _ = QuizConfig.objects.get_or_create(lesson=lesson)
        now = timezone.now()

        with transaction.atomic():
            progress, _ = LessonProgress.objects.select_for_update().get_or_create(
                user=request.user,
                lesson=lesson,
            )

            if progress.blocked_until and progress.blocked_until > now:
                return Response({
                    'detail': 'Попытки временно заблокированы.',
                    'blocked_until': progress.blocked_until,
                    'attempts_used': progress.attempts_used,
                    'max_attempts': config.max_attempts,
                }, status=status.HTTP_423_LOCKED)

            if config.max_attempts > 0 and progress.attempts_used >= config.max_attempts:
                if config.penalty_hours > 0:
                    progress.blocked_until = now + timedelta(hours=config.penalty_hours)
                    progress.save(update_fields=['blocked_until'])
                return Response({
                    'detail': 'Попытки исчерпаны.',
                    'blocked_until': progress.blocked_until,
                    'attempts_used': progress.attempts_used,
                    'max_attempts': config.max_attempts,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            correct_count = 0
            total_count = len(questions)
            incorrect_feedback = []

            for question in questions:
                raw_answer = submitted_answers.get(str(question.id), submitted_answers.get(question.id))
                correct_ids = {choice.id for choice in question.choices.all() if choice.is_correct}

                try:
                    if question.is_multiple:
                        if isinstance(raw_answer, list):
                            selected_ids = {int(value) for value in raw_answer}
                        elif raw_answer is None:
                            selected_ids = set()
                        else:
                            selected_ids = {int(raw_answer)}
                    else:
                        if raw_answer in (None, ''):
                            selected_ids = set()
                        else:
                            selected_ids = {int(raw_answer)}
                except (TypeError, ValueError):
                    selected_ids = set()

                is_correct = bool(selected_ids) and selected_ids == correct_ids
                if is_correct:
                    correct_count += 1
                elif question.explanation:
                    incorrect_feedback.append({
                        'question_id': question.id,
                        'explanation': question.explanation,
                    })

            score_percentage = int((correct_count * 100) / total_count) if total_count else 0
            is_passed = score_percentage >= config.passing_score_percentage

            progress.attempts_used += 1
            progress.score = score_percentage

            if is_passed:
                if not progress.is_completed:
                    progress.is_completed = True
                    progress.completed_at = now
                    record_daily_activity(request.user, ActivityLog.ACTION_LESSON_COMPLETED)
                progress.blocked_until = None
            elif config.max_attempts > 0 and progress.attempts_used >= config.max_attempts and config.penalty_hours > 0:
                progress.blocked_until = now + timedelta(hours=config.penalty_hours)

            progress.save(update_fields=['attempts_used', 'score', 'is_completed', 'completed_at', 'blocked_until'])

            visible_lesson_ids = list(
                student_visible_lessons_queryset(lesson.course).values_list('id', flat=True)
            )
            total_lessons = len(visible_lesson_ids)
            completed_lessons = LessonProgress.objects.filter(
                user=request.user,
                lesson_id__in=visible_lesson_ids,
                is_completed=True,
            ).count()
            course_progress_percentage = int((completed_lessons / total_lessons) * 100) if total_lessons else 0

        if is_passed:
            record_daily_activity(request.user, ActivityLog.ACTION_QUIZ_PASSED)

        return Response({
            'is_passed': is_passed,
            'score_percentage': score_percentage,
            'passing_score_percentage': config.passing_score_percentage,
            'correct_count': correct_count,
            'total_count': total_count,
            'attempts_used': progress.attempts_used,
            'max_attempts': config.max_attempts,
            'blocked_until': progress.blocked_until,
            'is_completed': progress.is_completed,
            'course_progress_percentage': course_progress_percentage,
            'incorrect_feedback': incorrect_feedback,
        })


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class UserActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requested_year = request.query_params.get('year')
        if requested_year is not None:
            year = get_activity_year(request)
            if year is None:
                return Response({'detail': 'Параметр year должен быть числом.'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = ActivityDaySerializer(
                get_yearly_activity_queryset(request.user, year, ActivityLog.STUDENT_ACTION_TYPES),
                many=True,
            )
            return Response(serializer.data)

        since_date = timezone.localdate() - timedelta(days=364)
        activity = (
            ActivityLog.objects
            .filter(
                user=request.user,
                date__gte=since_date,
                action_type__in=ActivityLog.STUDENT_ACTION_TYPES,
            )
            .values('date')
            .annotate(count=Sum('count'))
            .order_by('date')
        )
        serializer = ActivityDaySerializer(activity, many=True)
        return Response(serializer.data)


class TeacherActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.IS_TEACHER and not request.user.is_staff:
            return Response({'detail': 'Только преподаватели могут просматривать активность автора.'}, status=status.HTTP_403_FORBIDDEN)

        year = get_activity_year(request)
        if year is None:
            return Response({'detail': 'Параметр year должен быть числом.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ActivityDaySerializer(
            get_yearly_activity_queryset(request.user, year, ActivityLog.TEACHER_ACTION_TYPES),
            many=True,
        )
        return Response(serializer.data)


class PublicProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username):
        profile_user = get_object_or_404(
            User.objects.prefetch_related('skills', 'friends'),
            username=username,
        )
        serializer = PublicProfileSerializer(profile_user, context={'request': request})
        return Response(serializer.data)


class PublicUserActivityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username):
        profile_user = get_object_or_404(User, username=username)
        current_year = timezone.localdate().year
        registration_year = profile_user.date_joined.year
        requested_year = request.query_params.get('year')

        if requested_year is None:
            year = current_year
        else:
            try:
                year = int(requested_year)
            except (TypeError, ValueError):
                return Response({'detail': 'Параметр year должен быть числом.'}, status=status.HTTP_400_BAD_REQUEST)

        if year < registration_year or year > current_year:
            return Response(
                {'detail': f'Доступный диапазон годов: {registration_year}-{current_year}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ActivityDaySerializer(
            get_yearly_activity_queryset(profile_user, year, ActivityLog.STUDENT_ACTION_TYPES),
            many=True,
        )
        return Response(serializer.data)


class FriendToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, username):
        target_user = get_object_or_404(User, username=username)
        if target_user == request.user:
            return Response({'detail': 'Нельзя добавлять себя в друзья.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.friends.filter(pk=target_user.pk).exists():
            request.user.friends.remove(target_user)
            is_friend = False
            message = 'Пользователь удален из друзей.'
        else:
            request.user.friends.add(target_user)
            is_friend = True
            message = 'Пользователь добавлен в друзья.'

        return Response({
            'is_friend': is_friend,
            'friends_count': target_user.friends.count(),
            'message': message,
        })


class CommunityView(APIView):
    # Оставляем AllowAny, чтобы гости тоже могли видеть список
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. Сразу фильтруем: только обычные юзеры, не админы и не стафф
        users = User.objects.filter(
            is_staff=False, 
            is_superuser=False
        ).prefetch_related('skills', 'friends').order_by('-is_verified', 'username')

        # 2. Исключаем текущего пользователя из общего списка
        if request.user.is_authenticated:
            users = users.exclude(id=request.user.id)

        # Логика поиска по имени/био
        search_query = (request.query_params.get('search') or '').strip()
        if search_query:
            # Если юзер ищет кого-то конкретного, фильтры ICONTANS сработают тут
            users = users.filter(Q(username__icontains=search_query) | Q(bio__icontains=search_query))

        # Логика фильтрации по навыкам
        skills_query = request.query_params.get('skills', '')
        skill_names = [skill.strip() for skill in skills_query.split(',') if skill.strip()]
        for skill_name in skill_names:
            users = users.filter(skills__name__icontains=skill_name)

        serializer = CommunityUserSerializer(users.distinct(), many=True, context={'request': request})
        return Response(serializer.data)
    
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class CourseDetailAPIView(RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]


class LessonDetailAPIView(RetrieveAPIView):
    serializer_class = LessonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_staff or user.role == User.IS_TEACHER):
            return Lesson.objects.all()
        return Lesson.objects.filter(is_published=True)

    def get(self, request, *args, **kwargs):
        lesson = self.get_object()
        user = request.user

        if user.is_authenticated and user.role == User.IS_STUDENT:
            if not _student_can_access_lesson(user, lesson):
                return Response({'detail': 'Урок пока недоступен.'}, status=status.HTTP_403_FORBIDDEN)

        if user.is_authenticated and user.role == User.IS_TEACHER and not user.is_staff:
            if lesson.course.author_id != user.id and request.query_params.get('preview') == '1':
                return Response({'detail': 'Нельзя просматривать чужой урок в режиме preview.'}, status=status.HTTP_403_FORBIDDEN)

        return super().get(request, *args, **kwargs)


class GetQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        if Lesson.objects.filter(course=course).exists():
            return Response(
                {'detail': 'Курс использует новую систему тестов по урокам.'},
                status=status.HTTP_410_GONE,
            )
        questions = Question.objects.filter(course_id=course_id)
        if not questions.exists():
            return Response({'error': 'Вопросы для этого курса не найдены'}, status=status.HTTP_404_NOT_FOUND)

        data = []
        for question in questions:
            choices = Choice.objects.filter(question=question)
            data.append({
                'id': question.id,
                'text': question.text,
                'choices': [{'id': choice.id, 'text': choice.text} for choice in choices],
            })
        return Response(data)


class CheckQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        user = request.user
        if user.role != User.IS_STUDENT:
            return Response({'error': 'Только студенты могут проходить тесты'}, status=status.HTTP_403_FORBIDDEN)

        course = get_object_or_404(Course.objects.prefetch_related('skills_covered'), id=course_id)
        if Lesson.objects.filter(course=course).exists():
            return Response(
                {'detail': 'Курс использует новую систему тестов по урокам.'},
                status=status.HTTP_410_GONE,
            )
        questions = Question.objects.filter(course=course)
        answers = request.data.get('answers', {})

        correct_count = 0
        for question in questions:
            selected_choice_id = answers.get(str(question.id))
            if not selected_choice_id:
                continue

            try:
                choice = Choice.objects.get(id=selected_choice_id, question=question)
            except Choice.DoesNotExist:
                continue

            if choice.is_correct:
                correct_count += 1

        total_count = questions.count()
        is_passed = total_count > 0 and (correct_count / total_count) >= 0.8

        skills_added = []
        if is_passed:
            current_skill_ids = set(user.skills.values_list('id', flat=True))
            new_skills = [skill for skill in course.skills_covered.all() if skill.id not in current_skill_ids]
            if new_skills:
                user.skills.add(*new_skills)
                skills_added = [skill.name for skill in new_skills]

            record_daily_activity(user, ActivityLog.ACTION_QUIZ_PASSED)

        return Response({
            'is_passed': is_passed,
            'correct_count': correct_count,
            'total_count': total_count,
            'skills_added': skills_added,
        })


class StudentJobOffersView(generics.ListAPIView):
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return JobOffer.objects.filter(student=self.request.user).order_by('-created_at')


class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.IS_STUDENT:
            count = JobOffer.objects.filter(student=user, is_read_by_student=False).count()
            count += VacancyApplication.objects.filter(student=user, is_read_by_student=False).count()
        elif user.role == User.IS_EMPLOYER:
            count = JobOffer.objects.filter(employer=user, is_read_by_employer=False).exclude(status='pending').count()
            count += VacancyApplication.objects.filter(vacancy__employer=user, is_read_by_employer=False).count()
        else:
            count = 0
        return Response({'unread_count': count})


class JobOfferUpdateView(generics.UpdateAPIView):
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return JobOffer.objects.all()
        if user.role == User.IS_STUDENT:
            return JobOffer.objects.filter(student=user)
        if user.role == User.IS_EMPLOYER:
            return JobOffer.objects.filter(employer=user)
        return JobOffer.objects.none()

    def patch(self, request, *args, **kwargs):
        offer = self.get_object()
        user = request.user

        if user == offer.student:
            if 'status' in request.data:
                offer.status = request.data['status']
                offer.is_read_by_employer = False

            if 'is_read_by_student' in request.data:
                offer.is_read_by_student = request.data['is_read_by_student']

        elif user == offer.employer:
            if 'is_read_by_employer' in request.data:
                offer.is_read_by_employer = request.data['is_read_by_employer']

        offer.save()
        return Response(JobOfferSerializer(offer).data)


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class UserSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSettingsSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSettingsSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not request.user.check_password(old_password):
            return Response({'old_password': ['Старый пароль указан неверно.']}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'new_password': ['Новый пароль должен содержать минимум 8 символов.']}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'new_password': ['Новый пароль не должен совпадать со старым.']}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'confirm_password': ['Подтверждение пароля не совпадает.']}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Пароль успешно изменен.'})


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        if 'bio' in request.data:
            user.bio = request.data['bio']

        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        user.save()

        return Response({
            'message': 'Профиль обновлен',
            'bio': user.bio,
            'avatar': user.avatar.url if user.avatar else None,
        })



class VacancyListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = (
            Vacancy.objects
            .filter(status=Vacancy.STATUS_PUBLISHED)
            .select_related('employer')
            .prefetch_related('skills')
            .annotate(applications_count=Count('applications'))
            .order_by('-created_at')
        )

        search_query = (request.query_params.get('search') or '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(requirements__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(skills__name__icontains=search_query)
            )

        skills_query = request.query_params.get('skills', '')
        skill_names = [skill.strip() for skill in skills_query.split(',') if skill.strip()]
        for skill_name in skill_names:
            queryset = queryset.filter(skills__name__icontains=skill_name)

        work_format = request.query_params.get('work_format')
        if work_format:
            queryset = queryset.filter(work_format=work_format)

        employment_type = request.query_params.get('employment_type')
        if employment_type:
            queryset = queryset.filter(employment_type=employment_type)

        viewer_skill_ids = set()
        if request.user.is_authenticated and request.user.role == User.IS_STUDENT:
            viewer_skill_ids = set(request.user.skills.values_list('id', flat=True))
            if request.query_params.get('matched') == '1':
                if viewer_skill_ids:
                    queryset = queryset.filter(skills__id__in=viewer_skill_ids)
                else:
                    queryset = queryset.none()

        queryset = queryset.distinct()

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        vacancies = page if page is not None else list(queryset)

        application_map = {}
        if request.user.is_authenticated and request.user.role == User.IS_STUDENT and vacancies:
            vacancy_ids = [item.id for item in vacancies]
            application_map = {
                item.vacancy_id: item
                for item in VacancyApplication.objects.filter(student=request.user, vacancy_id__in=vacancy_ids)
            }

        serializer = VacancySerializer(
            vacancies,
            many=True,
            context={
                'request': request,
                'viewer_skill_ids': viewer_skill_ids,
                'application_map': application_map,
            },
        )

        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)


class StudentVacancyApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Отклики доступны только студентам.'}, status=status.HTTP_403_FORBIDDEN)

        queryset = (
            VacancyApplication.objects
            .filter(student=request.user)
            .select_related('vacancy', 'vacancy__employer', 'student')
            .prefetch_related('vacancy__skills', 'student__skills')
            .order_by('-created_at')
        )
        serializer = VacancyApplicationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)



class StudentVacancyApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Отклики доступны только студентам.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            application = (
                VacancyApplication.objects
                .select_related('vacancy', 'vacancy__employer', 'student')
                .prefetch_related('vacancy__skills', 'student__skills')
                .get(pk=pk, student=request.user)
            )
        except VacancyApplication.DoesNotExist:
            return Response({'detail': 'Отклик не найден.'}, status=status.HTTP_404_NOT_FOUND)

        update_fields = ['updated_at']

        if 'is_read_by_student' in request.data:
            application.is_read_by_student = bool(request.data.get('is_read_by_student'))
            update_fields.append('is_read_by_student')

        next_status = request.data.get('status')
        if next_status is not None:
            if next_status != VacancyApplication.STATUS_WITHDRAWN:
                return Response({'status': ['Студент может только отозвать свой отклик.']}, status=status.HTTP_400_BAD_REQUEST)
            if application.status in {VacancyApplication.STATUS_ACCEPTED, VacancyApplication.STATUS_REJECTED}:
                return Response({'detail': 'Нельзя отозвать отклик после финального решения работодателя.'}, status=status.HTTP_400_BAD_REQUEST)
            application.status = VacancyApplication.STATUS_WITHDRAWN
            application.is_read_by_employer = False
            update_fields.extend(['status', 'is_read_by_employer'])

        if len(update_fields) == 1:
            return Response({'detail': 'Нет данных для обновления.'}, status=status.HTTP_400_BAD_REQUEST)

        application.save(update_fields=list(dict.fromkeys(update_fields)))
        return Response(VacancyApplicationSerializer(application, context={'request': request}).data)


class VacancyApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, vacancy_id):
        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Откликаться на вакансии могут только студенты.'}, status=status.HTTP_403_FORBIDDEN)

        vacancy = get_object_or_404(Vacancy, id=vacancy_id, status=Vacancy.STATUS_PUBLISHED)
        message = (request.data.get('message') or '').strip()

        if len(message) > 1200:
            return Response({'message': ['Сообщение не должно превышать 1200 символов.']}, status=status.HTTP_400_BAD_REQUEST)

        application, created = VacancyApplication.objects.get_or_create(
            vacancy=vacancy,
            student=request.user,
            defaults={
                'message': message,
                'status': VacancyApplication.STATUS_PENDING,
                'is_read_by_student': True,
                'is_read_by_employer': False,
            },
        )

        if not created:
            return Response({'detail': 'Вы уже откликались на эту вакансию.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VacancyApplicationSerializer(application, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
