from django.db.models import Count
from rest_framework import serializers

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
    student_visible_lessons_queryset,
    User,
    Vacancy,
    VacancyApplication,
)


def _build_absolute_media_url(request, value):
    if not value:
        return ''
    if request:
        return request.build_absolute_uri(value)
    return value


def get_lesson_playback_payload(lesson, request=None):
    fallback_video_url = lesson.video_url or ''

    if lesson.type != Lesson.TYPE_VIDEO:
        return {
            'hls_status': 'no_video',
            'hls_manifest_url': '',
            'hls_error': '',
            'fallback_video_url': '',
            'playback_mode': 'no_video',
        }

    try:
        video_asset = lesson.video_asset
    except LessonVideo.DoesNotExist:
        return {
            'hls_status': 'missing',
            'hls_manifest_url': '',
            'hls_error': 'HLS-видео для урока не загружено.',
            'fallback_video_url': fallback_video_url,
            'playback_mode': 'fallback_video' if fallback_video_url else 'no_video',
        }

    manifest_url = _build_absolute_media_url(request, video_asset.m3u8_url)

    if video_asset.status == LessonVideo.STATUS_READY:
        if manifest_url:
            return {
                'hls_status': LessonVideo.STATUS_READY,
                'hls_manifest_url': manifest_url,
                'hls_error': '',
                'fallback_video_url': fallback_video_url,
                'playback_mode': 'hls_ready',
            }
        return {
            'hls_status': 'inconsistent',
            'hls_manifest_url': '',
            'hls_error': 'HLS-манифест отсутствует, хотя видео помечено как готовое.',
            'fallback_video_url': fallback_video_url,
            'playback_mode': 'fallback_video' if fallback_video_url else 'hls_failed',
        }

    if video_asset.status in {LessonVideo.STATUS_PENDING, LessonVideo.STATUS_PROCESSING}:
        return {
            'hls_status': video_asset.status,
            'hls_manifest_url': '',
            'hls_error': '',
            'fallback_video_url': fallback_video_url,
            'playback_mode': 'hls_processing',
        }

    if video_asset.status == LessonVideo.STATUS_FAILED:
        return {
            'hls_status': LessonVideo.STATUS_FAILED,
            'hls_manifest_url': '',
            'hls_error': video_asset.error_message or 'Не удалось подготовить HLS-видео.',
            'fallback_video_url': fallback_video_url,
            'playback_mode': 'fallback_video' if fallback_video_url else 'hls_failed',
        }

    return {
        'hls_status': 'unknown',
        'hls_manifest_url': '',
        'hls_error': 'Статус HLS-видео не распознан.',
        'fallback_video_url': fallback_video_url,
        'playback_mode': 'fallback_video' if fallback_video_url else 'hls_failed',
    }


def build_learning_skills(user):
    if user.role != User.IS_STUDENT:
        return []

    completed_skill_ids = set(user.skills.values_list('id', flat=True))
    started_courses = (
        Course.objects
        .filter(lessons__user_progress__user=user, lessons__user_progress__is_completed=True)
        .prefetch_related('skills_covered', 'lessons')
        .distinct()
    )
    completed_lessons_by_course = {
        row['lesson__course']: row['completed_count']
        for row in (
            LessonProgress.objects
            .filter(user=user, is_completed=True, lesson__course__in=started_courses)
            .values('lesson__course')
            .annotate(completed_count=Count('id'))
        )
    }

    learning_skills = []
    for course in started_courses:
        total_lessons = len(course.lessons.all())
        completed_lessons = completed_lessons_by_course.get(course.id, 0)

        if total_lessons == 0 or completed_lessons == 0:
            continue

        course_skills = list(course.skills_covered.all())
        if course_skills and all(skill.id in completed_skill_ids for skill in course_skills):
            continue

        progress_percentage = int((completed_lessons / total_lessons) * 100)
        for skill in course_skills:
            if skill.id in completed_skill_ids:
                continue

            learning_skills.append({
                'id': skill.id,
                'name': skill.name,
                'progress_percentage': progress_percentage,
                'course_name': course.title,
            })

    return learning_skills


class ViewerContextMixin:
    def _get_viewer(self):
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            return request.user
        return None

    def _get_viewer_friend_ids(self):
        if 'viewer_friend_ids' not in self.context:
            viewer = self._get_viewer()
            self.context['viewer_friend_ids'] = set(viewer.friends.values_list('id', flat=True)) if viewer else set()
        return self.context['viewer_friend_ids']

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            # Используем готовую функцию из твоего файла, чтобы приклеить домен API
            return _build_absolute_media_url(request, obj.avatar.url)
        return ''

    def get_registration_year(self, obj):
        return obj.date_joined.year

    def get_friends_count(self, obj):
        prefetched_friends = getattr(obj, '_prefetched_objects_cache', {}).get('friends')
        if prefetched_friends is not None:
            return len(prefetched_friends)
        return obj.friends.count()

    def get_common_friends_count(self, obj):
        viewer = self._get_viewer()
        if not viewer or viewer.pk == obj.pk:
            return 0

        viewer_friend_ids = self._get_viewer_friend_ids()
        prefetched_friends = getattr(obj, '_prefetched_objects_cache', {}).get('friends')
        if prefetched_friends is not None:
            friend_ids = {friend.id for friend in prefetched_friends}
        else:
            friend_ids = set(obj.friends.values_list('id', flat=True))
        return len(friend_ids & viewer_friend_ids)

    def get_is_friend(self, obj):
        viewer = self._get_viewer()
        if not viewer or viewer.pk == obj.pk:
            return False
        return obj.pk in self._get_viewer_friend_ids()

    def get_is_self(self, obj):
        viewer = self._get_viewer()
        return bool(viewer and viewer.pk == obj.pk)

    def get_roles(self, obj):
        return [obj.role]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class UserSerializer(ViewerContextMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    skills = SkillSerializer(many=True, read_only=True)
    registration_year = serializers.SerializerMethodField()
    friends_count = serializers.SerializerMethodField()
    common_friends_count = serializers.SerializerMethodField()
    is_friend = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'roles',
            'avatar',
            'bio',
            'is_verified',
            'skills',
            'registration_year',
            'friends_count',
            'common_friends_count',
            'is_friend',
            'is_self',
        ]


class CommunityUserSerializer(ViewerContextMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    skills = SkillSerializer(many=True, read_only=True)
    registration_year = serializers.SerializerMethodField()
    friends_count = serializers.SerializerMethodField()
    common_friends_count = serializers.SerializerMethodField()
    is_friend = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'role',
            'roles',
            'avatar',
            'bio',
            'is_verified',
            'skills',
            'registration_year',
            'friends_count',
            'common_friends_count',
            'is_friend',
            'is_self',
        ]


class LearningSkillSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    course_name = serializers.CharField()


class ActivityDaySerializer(serializers.Serializer):
    date = serializers.DateField(format='%Y-%m-%d')
    count = serializers.IntegerField()


class UserProfileSerializer(ViewerContextMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    completed_skills = SkillSerializer(source='skills', many=True, read_only=True)
    learning_skills = serializers.SerializerMethodField()
    registration_year = serializers.SerializerMethodField()
    friends_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'bio',
            'avatar',
            'is_verified',
            'skills',
            'completed_skills',
            'learning_skills',
            'registration_year',
            'friends_count',
        ]

    def get_skills(self, obj):
        return [skill.name for skill in obj.skills.all()]

    def get_learning_skills(self, obj):
        return LearningSkillSerializer(build_learning_skills(obj), many=True).data


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'avatar',
            'bio',
            'location',
            'telegram',
            'github',
            'linkedin',
        ]
        read_only_fields = ['username', 'email']


class PublicProfileSerializer(ViewerContextMixin, serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    skills = SkillSerializer(many=True, read_only=True)
    learning_skills = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    registration_year = serializers.SerializerMethodField()
    friends_count = serializers.SerializerMethodField()
    is_friend = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'bio',
            'avatar',
            'is_verified',
            'skills',
            'learning_skills',
            'roles',
            'registration_year',
            'friends_count',
            'is_friend',
            'is_self',
        ]

    def get_learning_skills(self, obj):
        return LearningSkillSerializer(build_learning_skills(obj), many=True).data



class LessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    hls_status = serializers.SerializerMethodField()
    hls_manifest_url = serializers.SerializerMethodField()
    hls_error = serializers.SerializerMethodField()
    fallback_video_url = serializers.SerializerMethodField()
    playback_mode = serializers.SerializerMethodField()
    module = serializers.PrimaryKeyRelatedField(queryset=Module.objects.all(), required=False, allow_null=True, write_only=True)
    module_id = serializers.IntegerField(source='module.id', read_only=True)
    lesson_type = serializers.CharField(source='type', read_only=True)
    # For quiz/final_exam lessons, content can be empty. DRF's default behavior trims
    # whitespace and treats " " as blank, so we explicitly allow blank here and
    # validate conditionally by lesson type below.
    content = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)

    class Meta:
        model = Lesson
        fields = [
            'id',
            'module',
            'module_id',
            'title',
            'video_url',
            'content',
            'order',
            'type',
            'lesson_type',
            'is_published',
            'is_completed',
            'hls_status',
            'hls_manifest_url',
            'hls_error',
            'fallback_video_url',
            'playback_mode',
        ]

    def validate(self, attrs):
        lesson_type = attrs.get('type') or getattr(self.instance, 'type', None)
        content = attrs.get('content', None)

        if lesson_type in {Lesson.TYPE_QUIZ, Lesson.TYPE_FINAL_EXAM}:
            # Allow empty content; normalize None/whitespace-only to empty string.
            if content is None or (isinstance(content, str) and content.strip() == ''):
                attrs['content'] = ''
            return attrs

        # For video/text lessons, keep content required and non-blank.
        if lesson_type in {Lesson.TYPE_VIDEO, Lesson.TYPE_TEXT}:
            if content is None or (isinstance(content, str) and content.strip() == ''):
                raise serializers.ValidationError({'content': ['This field may not be blank.']})

        return attrs

    def get_is_completed(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user.is_authenticated:
            return LessonProgress.objects.filter(user=user, lesson=obj, is_completed=True).exists()
        return False

    def _playback_payload(self, obj):
        cached = getattr(obj, '_playback_payload_cache', None)
        if cached is None:
            request = self.context.get('request')
            cached = get_lesson_playback_payload(obj, request=request)
            obj._playback_payload_cache = cached
        return cached

    def get_hls_status(self, obj):
        return self._playback_payload(obj)['hls_status']

    def get_hls_manifest_url(self, obj):
        return self._playback_payload(obj)['hls_manifest_url']

    def get_hls_error(self, obj):
        return self._playback_payload(obj)['hls_error']

    def get_fallback_video_url(self, obj):
        return self._playback_payload(obj)['fallback_video_url']

    def get_playback_mode(self, obj):
        return self._playback_payload(obj)['playback_mode']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_anonymous:
            data['video_url'] = None
            data['content'] = None
            data['hls_manifest_url'] = ''
            data['fallback_video_url'] = ''
            data['playback_mode'] = 'no_video'
        return data


class LessonVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonVideo
        fields = ['status', 'm3u8_url', 'error_message']


class LessonProgressSecondsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['watched_seconds']


class CourseSerializer(serializers.ModelSerializer):
    skills_covered = SkillSerializer(many=True, read_only=True)
    lessons = serializers.SerializerMethodField()
    author_name = serializers.CharField(source='author.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'image',
            'author_name',
            'skills_covered',
            'lessons',
            'progress_percentage',
            'sequential_unlock_enabled',
        ]

    def get_lessons(self, obj):
        lessons = student_visible_lessons_queryset(obj)
        return LessonSerializer(lessons, many=True, context=self.context).data

    def get_progress_percentage(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None:
            return 0

        if not user.is_authenticated:
            return 0

        visible_lesson_ids = list(student_visible_lessons_queryset(obj).values_list('id', flat=True))
        total_lessons = len(visible_lesson_ids)
        if total_lessons == 0:
            return 0

        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson_id__in=visible_lesson_ids,
            is_completed=True,
        ).count()
        return int((completed_lessons / total_lessons) * 100)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'role']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            role=validated_data.get('role', User.IS_STUDENT),
        )


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'choices']


class JobOfferSerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source='employer.username', read_only=True)
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = JobOffer
        fields = [
            'id',
            'employer',
            'student',
            'employer_name',
            'student_name',
            'message',
            'contact_link',
            'status',
            'created_at',
            'is_read_by_student',
            'is_read_by_employer',
        ]
        read_only_fields = ['employer', 'created_at']


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'order']
        read_only_fields = ['course']


class LessonAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = LessonAttachment
        fields = ['id', 'lesson', 'original_name', 'file', 'file_url', 'size', 'uploaded_at']
        read_only_fields = ['lesson', 'original_name', 'file_url', 'size', 'uploaded_at']

    def get_file_url(self, obj):
        return obj.file.url if obj.file else ''

    def get_size(self, obj):
        try:
            return obj.file.size
        except Exception:
            return 0


class QuizConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizConfig
        fields = [
            'id',
            'lesson',
            'passing_score_percentage',
            'max_attempts',
            'penalty_hours',
            'time_limit_minutes',
        ]
        read_only_fields = ['lesson']


class ChoiceWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']


class TeacherQuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceWriteSerializer(many=True)
    lesson_id = serializers.IntegerField(source='lesson.id', read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'course', 'lesson', 'lesson_id', 'text', 'is_multiple', 'explanation', 'choices']
        read_only_fields = ['course']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if choices_data is not None:
            existing_choices = {choice.id: choice for choice in instance.choices.all()}
            keep_ids = set()

            for choice_data in choices_data:
                choice_id = choice_data.get('id')
                if choice_id and choice_id in existing_choices:
                    choice = existing_choices[choice_id]
                    choice.text = choice_data.get('text', choice.text)
                    choice.is_correct = choice_data.get('is_correct', choice.is_correct)
                    choice.save(update_fields=['text', 'is_correct'])
                    keep_ids.add(choice.id)
                else:
                    choice = Choice.objects.create(
                        question=instance,
                        text=choice_data.get('text', ''),
                        is_correct=choice_data.get('is_correct', False),
                    )
                    keep_ids.add(choice.id)

            instance.choices.exclude(id__in=keep_ids).delete()

        return instance


class StudentAttachmentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='original_name')
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = LessonAttachment
        fields = ['id', 'name', 'file_url', 'file_size']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return ''
        url = obj.file.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_file_size(self, obj):
        try:
            return obj.file.size
        except Exception:
            return 0


class StudentOutlineLessonSerializer(serializers.ModelSerializer):
    is_completed = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    watched_seconds = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    blocked_until = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id',
            'title',
            'type',
            'order',
            'is_published',
            'is_completed',
            'is_locked',
            'content',
            'video_url',
            'watched_seconds',
            'attachments',
            'blocked_until',
            'attempts_used',
        ]

    def _get_progress(self, obj):
        progress_map = self.context.get('progress_map', {})
        return progress_map.get(obj.id)

    def get_is_completed(self, obj):
        progress = self._get_progress(obj)
        return bool(progress and progress.is_completed)

    def get_is_locked(self, obj):
        locked_ids = self.context.get('locked_lesson_ids', set())
        return obj.id in locked_ids

    def get_watched_seconds(self, obj):
        progress = self._get_progress(obj)
        return progress.watched_seconds if progress else 0

    def get_attachments(self, obj):
        serializer = StudentAttachmentSerializer(
            obj.attachments.all(),
            many=True,
            context=self.context,
        )
        return serializer.data

    def get_blocked_until(self, obj):
        progress = self._get_progress(obj)
        if not progress or not progress.blocked_until:
            return None
        return progress.blocked_until

    def get_attempts_used(self, obj):
        progress = self._get_progress(obj)
        return progress.attempts_used if progress else 0


class StudentOutlineModuleSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'order', 'lessons']

    def get_lessons(self, obj):
        lessons = getattr(obj, '_visible_lessons', list(obj.lessons.all()))
        serializer = StudentOutlineLessonSerializer(
            lessons,
            many=True,
            context=self.context,
        )
        return serializer.data


class CourseOutlineSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'modules', 'sequential_unlock_enabled']

    def get_modules(self, obj):
        modules = getattr(obj, '_visible_modules', list(obj.modules.all()))
        serializer = StudentOutlineModuleSerializer(
            modules,
            many=True,
            context=self.context,
        )
        return serializer.data


class StudentQuizChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text']


class StudentQuizQuestionSerializer(serializers.ModelSerializer):
    choices = StudentQuizChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'is_multiple', 'choices']



class VacancySerializer(serializers.ModelSerializer):
    employer_name = serializers.CharField(source='employer.username', read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    applications_count = serializers.SerializerMethodField()
    match_count = serializers.SerializerMethodField()
    is_matching = serializers.SerializerMethodField()
    application_id = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()

    class Meta:
        model = Vacancy
        fields = [
            'id',
            'employer',
            'employer_name',
            'company_name',
            'title',
            'description',
            'requirements',
            'skills',
            'work_format',
            'employment_type',
            'location',
            'salary_from',
            'salary_to',
            'contact_link',
            'status',
            'created_at',
            'updated_at',
            'applications_count',
            'match_count',
            'is_matching',
            'application_id',
            'application_status',
        ]
        read_only_fields = ['employer', 'created_at', 'updated_at']

    def _application_for(self, obj):
        application_map = self.context.get('application_map') or {}
        return application_map.get(obj.id)

    def get_applications_count(self, obj):
        count = getattr(obj, 'applications_count', None)
        if count is not None:
            return count
        return obj.applications.count()

    def get_match_count(self, obj):
        viewer_skill_ids = self.context.get('viewer_skill_ids')
        if viewer_skill_ids is None:
            return 0

        prefetched_skills = getattr(obj, '_prefetched_objects_cache', {}).get('skills')
        if prefetched_skills is not None:
            vacancy_skill_ids = {skill.id for skill in prefetched_skills}
        else:
            vacancy_skill_ids = set(obj.skills.values_list('id', flat=True))
        return len(vacancy_skill_ids & viewer_skill_ids)

    def get_is_matching(self, obj):
        return self.get_match_count(obj) > 0

    def get_application_id(self, obj):
        application = self._application_for(obj)
        return application.id if application else None

    def get_application_status(self, obj):
        application = self._application_for(obj)
        return application.status if application else None


class VacancyWriteSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    skill_names = serializers.ListField(child=serializers.CharField(max_length=100), write_only=True, required=False)

    class Meta:
        model = Vacancy
        fields = [
            'id',
            'company_name',
            'title',
            'description',
            'requirements',
            'skills',
            'skill_ids',
            'skill_names',
            'work_format',
            'employment_type',
            'location',
            'salary_from',
            'salary_to',
            'contact_link',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_title(self, value):
        value = (value or '').strip()
        if len(value) < 3:
            raise serializers.ValidationError('Название вакансии должно содержать минимум 3 символа.')
        return value

    def validate_description(self, value):
        value = (value or '').strip()
        if len(value) < 20:
            raise serializers.ValidationError('Описание должно содержать минимум 20 символов.')
        return value

    def validate_contact_link(self, value):
        value = (value or '').strip()
        lowered = value.lower()
        if lowered.startswith('javascript:') or '<' in value or '>' in value:
            raise serializers.ValidationError('Контактная ссылка содержит недопустимые символы.')
        return value

    def validate(self, attrs):
        salary_from = attrs.get('salary_from')
        salary_to = attrs.get('salary_to')
        if salary_from and salary_to and salary_from > salary_to:
            raise serializers.ValidationError({'salary_to': 'Верхняя граница зарплаты не может быть меньше нижней.'})
        return attrs

    def _sync_skills(self, vacancy, skill_ids=None, skill_names=None):
        skills = []
        if skill_ids:
            skills.extend(list(Skill.objects.filter(id__in=skill_ids)))
        if skill_names:
            for raw_name in skill_names:
                name = (raw_name or '').strip()
                if not name:
                    continue
                skill, _ = Skill.objects.get_or_create(name=name[:100])
                skills.append(skill)
        if skill_ids is not None or skill_names is not None:
            vacancy.skills.set(skills)

    def create(self, validated_data):
        skill_ids = validated_data.pop('skill_ids', None)
        skill_names = validated_data.pop('skill_names', None)
        vacancy = Vacancy.objects.create(**validated_data)
        self._sync_skills(vacancy, skill_ids, skill_names)
        return vacancy

    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skill_ids', None)
        skill_names = validated_data.pop('skill_names', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        self._sync_skills(instance, skill_ids, skill_names)
        return instance


class VacancyApplicationSerializer(serializers.ModelSerializer):
    vacancy = VacancySerializer(read_only=True)
    vacancy_id = serializers.IntegerField(source='vacancy.id', read_only=True)
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_avatar = serializers.SerializerMethodField()
    student_skills = SkillSerializer(source='student.skills', many=True, read_only=True)

    class Meta:
        model = VacancyApplication
        fields = [
            'id',
            'vacancy',
            'vacancy_id',
            'student_id',
            'student_username',
            'student_email',
            'student_avatar',
            'student_skills',
            'message',
            'status',
            'is_read_by_student',
            'is_read_by_employer',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_student_avatar(self, obj):
        if obj.student.avatar:
            request = self.context.get('request')
            return _build_absolute_media_url(request, obj.student.avatar.url)
        return ''