from rest_framework import status
from rest_framework.test import APITestCase

from .models import Course, JobOffer, Lesson, User, Vacancy, VacancyApplication


class ElCourseSmokeTests(APITestCase):
    def create_user(self, username, role):
        return User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='StrongPass123',
            role=role,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_course(self, author=None, title='Smoke course'):
        author = author or self.create_user('teacher-owner', User.IS_TEACHER)
        return Course.objects.create(
            author=author,
            title=title,
            description='Course created by smoke tests.',
        )

    def create_lesson(self, course, title='Smoke lesson', is_published=True, order=0):
        return Lesson.objects.create(
            course=course,
            title=title,
            type=Lesson.TYPE_VIDEO,
            content='Lesson content.',
            order=order,
            is_published=is_published,
        )

    def create_vacancy(self, employer=None, status_value=Vacancy.STATUS_PUBLISHED):
        employer = employer or self.create_user('employer-owner', User.IS_EMPLOYER)
        return Vacancy.objects.create(
            employer=employer,
            title='Junior Python Developer',
            company_name='Smoke Company',
            description='A published test vacancy with enough description.',
            requirements='Basic Python and Django knowledge.',
            status=status_value,
        )

    def test_register_student_teacher_and_employer(self):
        for role in [User.IS_STUDENT, User.IS_TEACHER, User.IS_EMPLOYER]:
            with self.subTest(role=role):
                response = self.client.post('/api/register/', {
                    'username': f'{role}-signup',
                    'email': f'{role}@example.com',
                    'password': 'StrongPass123',
                    'role': role,
                }, format='json')

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertTrue(User.objects.filter(username=f'{role}-signup', role=role).exists())

    def test_public_course_list_is_available(self):
        self.create_course()

        response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_guest_can_open_vacancies_list(self):
        self.create_vacancy()

        response = self.client.get('/api/vacancies/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_student_can_get_own_profile(self):
        student = self.create_user('profile-student', User.IS_STUDENT)
        self.authenticate(student)

        response = self.client.get('/api/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], student.username)

    def test_teacher_can_open_teacher_courses(self):
        teacher = self.create_user('course-teacher', User.IS_TEACHER)
        self.authenticate(teacher)

        response = self.client.get('/api/teacher/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employer_can_open_student_search(self):
        employer = self.create_user('search-employer', User.IS_EMPLOYER)
        self.create_user('search-student', User.IS_STUDENT)
        self.authenticate(employer)

        response = self.client.get('/api/employer/search/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_student_and_employer_cannot_open_teacher_courses(self):
        for user in [
            self.create_user('blocked-student', User.IS_STUDENT),
            self.create_user('blocked-employer', User.IS_EMPLOYER),
        ]:
            with self.subTest(role=user.role):
                self.authenticate(user)
                response = self.client.get('/api/teacher/courses/')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=None)

    def test_student_can_apply_to_published_vacancy(self):
        student = self.create_user('apply-student', User.IS_STUDENT)
        vacancy = self.create_vacancy()
        self.authenticate(student)

        response = self.client.post(
            f'/api/vacancies/{vacancy.id}/apply/',
            {'message': 'I would like to apply.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(VacancyApplication.objects.filter(vacancy=vacancy, student=student).exists())

    def test_guest_cannot_apply_to_vacancy(self):
        vacancy = self.create_vacancy()

        response = self.client.post(
            f'/api/vacancies/{vacancy.id}/apply/',
            {'message': 'Guest application should fail.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_can_see_own_vacancy_applications(self):
        student = self.create_user('applications-student', User.IS_STUDENT)
        vacancy = self.create_vacancy()
        VacancyApplication.objects.create(vacancy=vacancy, student=student, message='My application.')
        self.authenticate(student)

        response = self.client.get('/api/student/vacancy-applications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student_id'], student.id)

    def test_employer_can_see_applications_for_own_vacancies(self):
        employer = self.create_user('applications-employer', User.IS_EMPLOYER)
        student = self.create_user('applications-candidate', User.IS_STUDENT)
        vacancy = self.create_vacancy(employer=employer)
        VacancyApplication.objects.create(vacancy=vacancy, student=student, message='Candidate application.')
        self.authenticate(employer)

        response = self.client.get('/api/employer/vacancy-applications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student_id'], student.id)

    def test_foreign_job_offer_cannot_be_changed(self):
        owner_employer = self.create_user('offer-owner-employer', User.IS_EMPLOYER)
        other_employer = self.create_user('offer-other-employer', User.IS_EMPLOYER)
        student = self.create_user('offer-student', User.IS_STUDENT)
        offer = JobOffer.objects.create(
            employer=owner_employer,
            student=student,
            message='Private offer.',
            status='pending',
        )
        self.authenticate(other_employer)

        response = self.client.patch(
            f'/api/offers/{offer.id}/update/',
            {'is_read_by_employer': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        offer.refresh_from_db()
        self.assertEqual(offer.status, 'pending')

    def test_lesson_manifest_and_progress_require_lesson_access(self):
        teacher = self.create_user('lesson-teacher', User.IS_TEACHER)
        student = self.create_user('lesson-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        accessible_lesson = self.create_lesson(course, title='Published lesson', is_published=True, order=0)
        hidden_lesson = self.create_lesson(course, title='Hidden lesson', is_published=False, order=1)

        manifest_url = f'/api/lessons/{accessible_lesson.id}/video/manifest/'
        progress_url = f'/api/lessons/{accessible_lesson.id}/progress/'
        hidden_manifest_url = f'/api/lessons/{hidden_lesson.id}/video/manifest/'
        hidden_progress_url = f'/api/lessons/{hidden_lesson.id}/progress/'

        self.assertEqual(self.client.get(manifest_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(progress_url).status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate(student)
        self.assertEqual(self.client.get(manifest_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(progress_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(hidden_manifest_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(hidden_progress_url).status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(teacher)
        self.assertEqual(self.client.get(manifest_url).status_code, status.HTTP_200_OK)
