from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobOffer, User
from .serializers import JobOfferSerializer, UserSerializer


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
