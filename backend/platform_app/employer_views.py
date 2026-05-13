from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobOffer, User, Vacancy, VacancyApplication
from .serializers import JobOfferSerializer, UserSerializer, VacancyApplicationSerializer, VacancySerializer, VacancyWriteSerializer


class EmployerStudentSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({"error": "Доступ только для работодателей"}, status=403)

        skills_query = request.query_params.get('skills', '')
        users = User.objects.filter(role='student').prefetch_related('skills', 'friends').order_by('-is_verified', 'username')

        if skills_query:
            skill_list = [skill.strip() for skill in skills_query.split(',') if skill.strip()]
            for skill_name in skill_list:
                users = users.filter(skills__name__iexact=skill_name)
            users = users.distinct()

        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)


class EmployerJobOfferView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response(
                {"detail": "Офферы могут отправлять только работодатели."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student_id = request.data.get('student_id') or request.data.get('student')
        if not student_id:
            return Response(
                {"detail": "Не указан студент для оффера."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {"detail": "Студент не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        existing_offer = (
            JobOffer.objects
            .filter(employer=request.user, student=student, status__in=['pending', 'accepted'])
            .order_by('-created_at')
            .first()
        )
        if existing_offer:
            return Response(
                {
                    "detail": "Активный оффер этому студенту уже отправлен.",
                    "existing_offer": JobOfferSerializer(existing_offer).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        offer = JobOffer.objects.create(
            employer=request.user,
            student=student,
            message=(request.data.get('message') or '').strip(),
            contact_link=(request.data.get('contact_link') or '').strip(),
            status='pending',
            is_read_by_student=False,
            is_read_by_employer=True,
        )

        return Response(JobOfferSerializer(offer).data, status=status.HTTP_201_CREATED)


class EmployerOffersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'employer':
            return Response({"error": "Доступ только для работодателей"}, status=403)

        offers = JobOffer.objects.filter(employer=request.user).order_by('-created_at')
        serializer = JobOfferSerializer(offers, many=True)
        return Response(serializer.data)



class EmployerVacancyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Доступ только для работодателей.'}, status=status.HTTP_403_FORBIDDEN)

        vacancies = (
            Vacancy.objects
            .filter(employer=request.user)
            .prefetch_related('skills')
            .order_by('-created_at')
        )
        serializer = VacancySerializer(vacancies, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Создавать вакансии могут только работодатели.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = VacancyWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        vacancy = serializer.save(employer=request.user)
        return Response(VacancySerializer(vacancy, context={'request': request}).data, status=status.HTTP_201_CREATED)


class EmployerVacancyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return Vacancy.objects.prefetch_related('skills').get(pk=pk, employer=request.user)

    def patch(self, request, pk):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Доступ только для работодателей.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            vacancy = self.get_object(request, pk)
        except Vacancy.DoesNotExist:
            return Response({'detail': 'Вакансия не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = VacancyWriteSerializer(vacancy, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        vacancy = serializer.save()
        return Response(VacancySerializer(vacancy, context={'request': request}).data)

    def delete(self, request, pk):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Доступ только для работодателей.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            vacancy = self.get_object(request, pk)
        except Vacancy.DoesNotExist:
            return Response({'detail': 'Вакансия не найдена.'}, status=status.HTTP_404_NOT_FOUND)

        vacancy.status = Vacancy.STATUS_CLOSED
        vacancy.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmployerVacancyApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Доступ только для работодателей.'}, status=status.HTTP_403_FORBIDDEN)

        queryset = (
            VacancyApplication.objects
            .filter(vacancy__employer=request.user)
            .select_related('vacancy', 'vacancy__employer', 'student')
            .prefetch_related('vacancy__skills', 'student__skills')
            .order_by('-created_at')
        )

        vacancy_id = request.query_params.get('vacancy_id')
        if vacancy_id:
            queryset = queryset.filter(vacancy_id=vacancy_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = VacancyApplicationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class EmployerVacancyApplicationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != 'employer' and not request.user.is_staff:
            return Response({'detail': 'Доступ только для работодателей.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            application = VacancyApplication.objects.select_related('vacancy', 'student').get(pk=pk, vacancy__employer=request.user)
        except VacancyApplication.DoesNotExist:
            return Response({'detail': 'Отклик не найден.'}, status=status.HTTP_404_NOT_FOUND)

        if 'is_read_by_employer' in request.data and 'status' not in request.data:
            application.is_read_by_employer = bool(request.data.get('is_read_by_employer'))
            application.save(update_fields=['is_read_by_employer', 'updated_at'])
            return Response(VacancyApplicationSerializer(application, context={'request': request}).data)

        next_status = request.data.get('status')
        allowed = {
            VacancyApplication.STATUS_PENDING,
            VacancyApplication.STATUS_VIEWED,
            VacancyApplication.STATUS_ACCEPTED,
            VacancyApplication.STATUS_REJECTED,
        }
        if next_status not in allowed:
            return Response({'status': ['Недопустимый статус отклика.']}, status=status.HTTP_400_BAD_REQUEST)

        application.status = next_status
        application.is_read_by_student = False
        application.is_read_by_employer = True
        application.save(update_fields=['status', 'is_read_by_student', 'is_read_by_employer', 'updated_at'])
        return Response(VacancyApplicationSerializer(application, context={'request': request}).data)
