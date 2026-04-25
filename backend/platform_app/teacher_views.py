from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .serializers import LessonSerializer
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Course, Question, Choice, Lesson
from .serializers import CourseSerializer, QuestionSerializer


class TeacherLessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        # Проверяем, что курс принадлежит именно этому учителю
        return Lesson.objects.filter(
            course__id=course_id, 
            course__author=self.request.user
        ).order_by('order')

    def perform_create(self, serializer):
        course = Course.objects.get(id=self.kwargs['course_id'], author=self.request.user)
        serializer.save(course=course)


class TeacherCourseListView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Проверка: если пользователь не учитель, закрываем доступ
        if self.request.user.role != 'teacher':
            raise PermissionDenied("У вас нет прав преподавателя")
        # Возвращаем только те курсы, где текущий юзер — автор
        return Course.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != 'teacher':
            raise PermissionDenied("Только преподаватели могут создавать курсы")
        
        # 1. Сохраняем сам курс в базу
        course = serializer.save(author=self.request.user)
        
        # 2. Вытаскиваем все галочки навыков из FormData (getlist собирает их в массив)
        skills = self.request.data.getlist('skills_covered')
        
        # 3. Намертво привязываем эти навыки к созданному курсу
        if skills:
            course.skills_covered.set(skills)


# 1. Редактирование и удаление курса
class TeacherCourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(author=self.request.user)
        
    # ДОБАВЛЯЕМ ПЕРЕХВАТ ПРИ ОБНОВЛЕНИИ (РЕДАКТИРОВАНИИ)
    def perform_update(self, serializer):
        # 1. Обновляем базовые данные курса (название, описание)
        course = serializer.save()
        
        # 2. Если во время обновления пришел новый список навыков
        if 'skills_covered' in self.request.data:
            skills = self.request.data.getlist('skills_covered')
            course.skills_covered.set(skills)
            
class TeacherQuizUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        questions = Question.objects.filter(course_id=course_id, course__author=request.user)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)

    def post(self, request, course_id):
        course = Course.objects.get(id=course_id, author=request.user)
        data = request.data # Ожидаем структуру вопроса с ответами
        
        question = Question.objects.create(course=course, text=data['text'])
        for choice_data in data['choices']:
            Choice.objects.create(
                question=question,
                text=choice_data['text'],
                is_correct=choice_data['is_correct']
            )
        
        return Response({"message": "Вопрос добавлен"}, status=status.HTTP_201_CREATED)