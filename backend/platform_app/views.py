import base64
import os
from datetime import date, timedelta
from pathlib import Path

from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from xhtml2pdf import pisa
except ImportError:  # pragma: no cover - depends on local optional dependency
    pisa = None

from .models import ActivityLog, Choice, Course, JobOffer, Lesson, LessonProgress, LessonVideo, Question, Skill, User
from .serializers import (
    ActivityDaySerializer,
    CommunityUserSerializer,
    CourseSerializer,
    JobOfferSerializer,
    LessonProgressSecondsSerializer,
    LessonSerializer,
    LessonVideoSerializer,
    PublicProfileSerializer,
    RegisterSerializer,
    SkillSerializer,
    UserSettingsSerializer,
    UserProfileSerializer,
)
from .tasks import convert_to_hls


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

        total_lessons = lesson.course.lessons.count()
        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson__course=lesson.course,
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
        lesson = get_object_or_404(Lesson, id=lesson_id)
        video_asset, _ = LessonVideo.objects.get_or_create(lesson=lesson)
        payload = LessonVideoSerializer(video_asset).data

        manifest_url = payload.get('m3u8_url')
        if manifest_url:
            payload['m3u8_url'] = request.build_absolute_uri(manifest_url)

        return Response(payload)


class LessonWatchProgressView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lesson_id):
        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Только студенты могут получать прогресс просмотра.'}, status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson, id=lesson_id)
        progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

        return Response({
            'watched_seconds': progress.watched_seconds,
            'is_completed': progress.is_completed,
        })

    def patch(self, request, lesson_id):
        if request.user.role != User.IS_STUDENT and not request.user.is_staff:
            return Response({'detail': 'Только студенты могут обновлять прогресс просмотра.'}, status=status.HTTP_403_FORBIDDEN)

        lesson = get_object_or_404(Lesson, id=lesson_id)
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
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class GetQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
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
        elif user.role == User.IS_EMPLOYER:
            count = JobOffer.objects.filter(employer=user, is_read_by_employer=False).exclude(status='pending').count()
        else:
            count = 0
        return Response({'unread_count': count})


class JobOfferUpdateView(generics.UpdateAPIView):
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]
    queryset = JobOffer.objects.all()

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
