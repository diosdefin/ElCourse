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
    User,
)


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
        return obj.avatar.url if obj.avatar else None

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_anonymous:
            data['video_url'] = None
            data['content'] = None
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
    lessons = LessonSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'image', 'author_name', 'skills_covered', 'lessons', 'progress_percentage']

    def get_progress_percentage(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None:
            return 0

        if not user.is_authenticated:
            return 0

        total_lessons = obj.lessons.count()
        if total_lessons == 0:
            return 0

        completed_lessons = LessonProgress.objects.filter(
            user=user,
            lesson__course=obj,
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
        fields = ['id', 'title', 'modules']

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
