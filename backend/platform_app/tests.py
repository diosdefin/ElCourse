from rest_framework import status
from rest_framework.test import APITestCase

from .models import Choice, Course, JobOffer, Lesson, LessonProgress, LessonVideo, Module, Question, User, Vacancy, VacancyApplication


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

    def create_module(self, course, title='Smoke module', order=0):
        return Module.objects.create(course=course, title=title, order=order)

    def create_question(self, course, text='Question?', lesson=None, correct='Correct', wrong='Wrong'):
        question = Question.objects.create(
            course=course,
            lesson=lesson,
            text=text,
            is_multiple=False,
            explanation='Explanation.',
        )
        correct_choice = Choice.objects.create(question=question, text=correct, is_correct=True)
        wrong_choice = Choice.objects.create(question=question, text=wrong, is_correct=False)
        return question, correct_choice, wrong_choice

    def create_lesson_video(self, lesson, status_value=LessonVideo.STATUS_READY, m3u8_url='/media/hls/test/master.m3u8', error_message=''):
        return LessonVideo.objects.create(
            lesson=lesson,
            status=status_value,
            m3u8_url=m3u8_url,
            error_message=error_message,
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
        self.assertEqual(self.client.get(manifest_url).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.client.get(progress_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(hidden_manifest_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(hidden_progress_url).status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(teacher)
        self.assertEqual(self.client.get(manifest_url).status_code, status.HTTP_409_CONFLICT)

    def test_student_gets_manifest_for_ready_unlocked_hls_lesson(self):
        teacher = self.create_user('hls-ready-teacher', User.IS_TEACHER)
        student = self.create_user('hls-ready-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = self.create_lesson(course, title='HLS ready lesson', is_published=True, order=0)
        self.create_lesson_video(lesson, status_value=LessonVideo.STATUS_READY, m3u8_url='/media/hls/ready/master.m3u8')

        self.authenticate(student)
        response = self.client.get(f'/api/lessons/{lesson.id}/video/manifest/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], LessonVideo.STATUS_READY)
        self.assertTrue(response.data['manifest_url'].endswith('/media/hls/ready/master.m3u8'))

    def test_student_cannot_get_manifest_for_locked_or_unpublished_lesson(self):
        teacher = self.create_user('hls-guard-teacher', User.IS_TEACHER)
        student = self.create_user('hls-guard-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        unlocked = self.create_lesson(course, title='Unlocked video', is_published=True, order=0)
        locked = self.create_lesson(course, title='Locked video', is_published=True, order=1)
        hidden = self.create_lesson(course, title='Hidden video', is_published=False, order=2)
        self.create_lesson_video(unlocked)
        self.create_lesson_video(locked)
        self.create_lesson_video(hidden)

        self.authenticate(student)
        self.assertEqual(self.client.get(f'/api/lessons/{unlocked.id}/video/manifest/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f'/api/lessons/{locked.id}/video/manifest/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(f'/api/lessons/{hidden.id}/video/manifest/').status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_get_manifest_for_own_ready_lesson_but_other_teacher_cannot(self):
        owner = self.create_user('hls-owner-teacher', User.IS_TEACHER)
        other = self.create_user('hls-other-teacher', User.IS_TEACHER)
        course = self.create_course(author=owner)
        lesson = self.create_lesson(course, title='Owned video lesson', is_published=False, order=0)
        self.create_lesson_video(lesson)

        self.authenticate(owner)
        self.assertEqual(self.client.get(f'/api/lessons/{lesson.id}/video/manifest/').status_code, status.HTTP_200_OK)

        self.authenticate(other)
        self.assertEqual(self.client.get(f'/api/lessons/{lesson.id}/video/manifest/').status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_lesson_video_does_not_create_fake_pending_manifest(self):
        teacher = self.create_user('missing-video-teacher', User.IS_TEACHER)
        student = self.create_user('missing-video-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = self.create_lesson(course, title='No HLS uploaded', is_published=True, order=0)

        self.authenticate(student)
        response = self.client.get(f'/api/lessons/{lesson.id}/video/manifest/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['status'], 'missing')
        self.assertFalse(LessonVideo.objects.filter(lesson=lesson).exists())

    def test_processing_failed_and_inconsistent_hls_states_are_reported_explicitly(self):
        teacher = self.create_user('hls-states-teacher', User.IS_TEACHER)
        student = self.create_user('hls-states-student', User.IS_STUDENT)
        processing_course = self.create_course(author=teacher, title='Processing course')
        failed_course = self.create_course(author=teacher, title='Failed course')
        inconsistent_course = self.create_course(author=teacher, title='Inconsistent course')
        processing_lesson = self.create_lesson(processing_course, title='Processing video', is_published=True, order=0)
        failed_lesson = self.create_lesson(failed_course, title='Failed video', is_published=True, order=0)
        inconsistent_lesson = self.create_lesson(inconsistent_course, title='Inconsistent video', is_published=True, order=0)
        self.create_lesson_video(processing_lesson, status_value=LessonVideo.STATUS_PROCESSING, m3u8_url='')
        self.create_lesson_video(failed_lesson, status_value=LessonVideo.STATUS_FAILED, m3u8_url='', error_message='ffmpeg failed')
        self.create_lesson_video(inconsistent_lesson, status_value=LessonVideo.STATUS_READY, m3u8_url='')

        self.authenticate(student)

        processing_response = self.client.get(f'/api/lessons/{processing_lesson.id}/video/manifest/')
        failed_response = self.client.get(f'/api/lessons/{failed_lesson.id}/video/manifest/')
        inconsistent_response = self.client.get(f'/api/lessons/{inconsistent_lesson.id}/video/manifest/')

        self.assertEqual(processing_response.status_code, status.HTTP_200_OK)
        self.assertEqual(processing_response.data['status'], LessonVideo.STATUS_PROCESSING)

        self.assertEqual(failed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(failed_response.data['status'], LessonVideo.STATUS_FAILED)
        self.assertEqual(failed_response.data['error_message'], 'ffmpeg failed')

        self.assertEqual(inconsistent_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(inconsistent_response.data['status'], 'inconsistent')

    def test_lesson_detail_exposes_consistent_playback_fields(self):
        teacher = self.create_user('lesson-detail-hls-teacher', User.IS_TEACHER)
        student = self.create_user('lesson-detail-hls-student', User.IS_STUDENT)
        video_course = self.create_course(author=teacher, title='Playback video course')
        text_course = self.create_course(author=teacher, title='Playback text course')
        video_lesson = Lesson.objects.create(
            course=video_course,
            title='Playback video lesson',
            type=Lesson.TYPE_VIDEO,
            content='Video content.',
            video_url='https://cdn.example.com/direct.mp4',
            order=0,
            is_published=True,
        )
        text_lesson = Lesson.objects.create(
            course=text_course,
            title='Playback text lesson',
            type=Lesson.TYPE_TEXT,
            content='Text content.',
            order=0,
            is_published=True,
        )
        self.create_lesson_video(video_lesson, status_value=LessonVideo.STATUS_READY, m3u8_url='/media/hls/playback/master.m3u8')

        self.authenticate(student)
        video_response = self.client.get(f'/api/lessons/{video_lesson.id}/')
        text_response = self.client.get(f'/api/lessons/{text_lesson.id}/')

        self.assertEqual(video_response.status_code, status.HTTP_200_OK)
        self.assertEqual(video_response.data['hls_status'], LessonVideo.STATUS_READY)
        self.assertEqual(video_response.data['playback_mode'], 'hls_ready')
        self.assertTrue(video_response.data['hls_manifest_url'].endswith('/media/hls/playback/master.m3u8'))
        self.assertEqual(video_response.data['fallback_video_url'], 'https://cdn.example.com/direct.mp4')

        self.assertEqual(text_response.status_code, status.HTTP_200_OK)
        self.assertEqual(text_response.data['hls_status'], 'no_video')
        self.assertEqual(text_response.data['playback_mode'], 'no_video')
        self.assertEqual(text_response.data['hls_manifest_url'], '')
        self.assertEqual(text_response.data['fallback_video_url'], '')

    def test_teacher_delete_module_removes_lessons_from_student_outline(self):
        teacher = self.create_user('module-delete-teacher', User.IS_TEACHER)
        student = self.create_user('module-delete-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        module = self.create_module(course, title='Module to delete', order=0)
        lesson = Lesson.objects.create(
            course=course,
            module=module,
            title='Lesson in module',
            type=Lesson.TYPE_TEXT,
            content='Text content.',
            order=0,
            is_published=True,
        )

        self.authenticate(student)
        outline_before = self.client.get(f'/api/courses/{course.id}/outline/')
        self.assertEqual(outline_before.status_code, status.HTTP_200_OK)
        lesson_ids_before = [
            item['id']
            for module_payload in outline_before.data['modules']
            for item in module_payload.get('lessons', [])
        ]
        self.assertIn(lesson.id, lesson_ids_before)

        self.authenticate(teacher)
        delete_response = self.client.delete(f'/api/teacher/modules/{module.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=lesson.id).exists())

        self.authenticate(student)
        outline_after = self.client.get(f'/api/courses/{course.id}/outline/')
        self.assertEqual(outline_after.status_code, status.HTTP_200_OK)
        lesson_ids_after = [
            item['id']
            for module_payload in outline_after.data['modules']
            for item in module_payload.get('lessons', [])
        ]
        self.assertNotIn(lesson.id, lesson_ids_after)

        lesson_response = self.client.get(f'/api/lessons/{lesson.id}/')
        self.assertEqual(lesson_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_direct_lesson_delete_removes_lesson_from_student_outline(self):
        teacher = self.create_user('lesson-delete-teacher', User.IS_TEACHER)
        student = self.create_user('lesson-delete-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        module = self.create_module(course, title='Existing module', order=0)
        lesson = Lesson.objects.create(
            course=course,
            module=module,
            title='Lesson to delete',
            type=Lesson.TYPE_TEXT,
            content='Text content.',
            order=0,
            is_published=True,
        )

        self.authenticate(teacher)
        delete_response = self.client.delete(f'/api/teacher/lessons/{lesson.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        self.authenticate(student)
        outline_response = self.client.get(f'/api/courses/{course.id}/outline/')
        self.assertEqual(outline_response.status_code, status.HTTP_200_OK)
        lesson_ids = [
            item['id']
            for module_payload in outline_response.data['modules']
            for item in module_payload.get('lessons', [])
        ]
        self.assertNotIn(lesson.id, lesson_ids)

    def test_unpublished_lessons_are_not_counted_in_student_progress(self):
        teacher = self.create_user('progress-teacher', User.IS_TEACHER)
        student = self.create_user('progress-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        published_lesson = Lesson.objects.create(
            course=course,
            title='Published text lesson',
            type=Lesson.TYPE_TEXT,
            content='Published content.',
            order=0,
            is_published=True,
        )
        Lesson.objects.create(
            course=course,
            title='Hidden draft lesson',
            type=Lesson.TYPE_TEXT,
            content='Draft content.',
            order=1,
            is_published=False,
        )

        self.authenticate(student)
        complete_response = self.client.post(f'/api/lessons/{published_lesson.id}/complete/', {}, format='json')
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.data['course_progress_percentage'], 100)
        self.assertTrue(complete_response.data['course_completed'])

        course_response = self.client.get(f'/api/courses/{course.id}/')
        self.assertEqual(course_response.status_code, status.HTTP_200_OK)
        self.assertEqual(course_response.data['progress_percentage'], 100)
        self.assertEqual(len(course_response.data['lessons']), 1)
        self.assertEqual(course_response.data['lessons'][0]['id'], published_lesson.id)

    def test_student_cannot_open_locked_lesson_directly_but_can_open_unlocked_lesson(self):
        teacher = self.create_user('lock-teacher', User.IS_TEACHER)
        student = self.create_user('lock-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        first_lesson = Lesson.objects.create(
            course=course,
            title='First lesson',
            type=Lesson.TYPE_TEXT,
            content='First content.',
            order=0,
            is_published=True,
        )
        second_lesson = Lesson.objects.create(
            course=course,
            title='Second lesson',
            type=Lesson.TYPE_TEXT,
            content='Second content.',
            order=1,
            is_published=True,
        )

        self.authenticate(student)
        first_response = self.client.get(f'/api/lessons/{first_lesson.id}/')
        second_response = self.client.get(f'/api/lessons/{second_lesson.id}/')

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_text_lesson_can_be_completed_without_video_and_updates_progress(self):
        teacher = self.create_user('text-teacher', User.IS_TEACHER)
        student = self.create_user('text-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = Lesson.objects.create(
            course=course,
            title='Text-only lesson',
            type=Lesson.TYPE_TEXT,
            content='Text-only content.',
            order=0,
            is_published=True,
        )

        self.authenticate(student)
        response = self.client.post(f'/api/lessons/{lesson.id}/complete/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_progress_percentage'], 100)
        self.assertTrue(
            LessonProgress.objects.filter(user=student, lesson=lesson, is_completed=True).exists()
        )

    def test_lesson_quiz_returns_only_questions_for_requested_lesson(self):
        teacher = self.create_user('lesson-quiz-teacher', User.IS_TEACHER)
        student = self.create_user('lesson-quiz-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson_one = Lesson.objects.create(course=course, title='Quiz 1', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        lesson_two = Lesson.objects.create(course=course, title='Quiz 2', type=Lesson.TYPE_QUIZ, content='', order=1, is_published=True)
        question_one, *_ = self.create_question(course, text='Question for lesson 1', lesson=lesson_one)
        self.create_question(course, text='Question for lesson 2', lesson=lesson_two)

        self.authenticate(student)
        response = self.client.get(f'/api/lessons/{lesson_one.id}/quiz/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['questions']), 1)
        self.assertEqual(response.data['questions'][0]['id'], question_one.id)

    def test_legacy_course_quiz_does_not_include_lesson_questions(self):
        teacher = self.create_user('legacy-quiz-teacher', User.IS_TEACHER)
        student = self.create_user('legacy-quiz-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = Lesson.objects.create(course=course, title='Lesson quiz', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        legacy_question, *_ = self.create_question(course, text='Legacy question', lesson=None)
        self.create_question(course, text='Lesson question', lesson=lesson)

        self.authenticate(student)
        response = self.client.get(f'/api/courses/{course.id}/quiz/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], legacy_question.id)

    def test_lesson_quiz_does_not_include_legacy_questions(self):
        teacher = self.create_user('no-legacy-mix-teacher', User.IS_TEACHER)
        student = self.create_user('no-legacy-mix-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = Lesson.objects.create(course=course, title='Lesson quiz', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        self.create_question(course, text='Legacy question', lesson=None)
        lesson_question, *_ = self.create_question(course, text='Lesson-only question', lesson=lesson)

        self.authenticate(student)
        response = self.client.get(f'/api/lessons/{lesson.id}/quiz/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['questions']), 1)
        self.assertEqual(response.data['questions'][0]['id'], lesson_question.id)

    def test_submit_lesson_quiz_rejects_foreign_question_and_answer_ids(self):
        teacher = self.create_user('foreign-answer-teacher', User.IS_TEACHER)
        student = self.create_user('foreign-answer-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson_one = Lesson.objects.create(course=course, title='Quiz 1', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        lesson_two = Lesson.objects.create(course=course, title='Quiz 2', type=Lesson.TYPE_QUIZ, content='', order=1, is_published=True)
        question_one, correct_one, _ = self.create_question(course, text='Question for lesson 1', lesson=lesson_one)
        question_two, correct_two, _ = self.create_question(course, text='Question for lesson 2', lesson=lesson_two)

        self.authenticate(student)

        foreign_question_response = self.client.post(
            f'/api/lessons/{lesson_one.id}/quiz/submit/',
            {'answers': {str(question_two.id): correct_two.id}},
            format='json',
        )
        self.assertEqual(foreign_question_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LessonProgress.objects.filter(user=student, lesson=lesson_one).exists())

        foreign_choice_response = self.client.post(
            f'/api/lessons/{lesson_one.id}/quiz/submit/',
            {'answers': {str(question_one.id): correct_two.id}},
            format='json',
        )
        self.assertEqual(foreign_choice_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LessonProgress.objects.filter(user=student, lesson=lesson_one).exists())

    def test_submit_lesson_quiz_rejects_legacy_question_ids(self):
        teacher = self.create_user('legacy-submit-teacher', User.IS_TEACHER)
        student = self.create_user('legacy-submit-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = Lesson.objects.create(course=course, title='Lesson quiz', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        lesson_question, correct_choice, _ = self.create_question(course, text='Lesson question', lesson=lesson)
        legacy_question, legacy_correct, _ = self.create_question(course, text='Legacy question', lesson=None)

        self.authenticate(student)
        response = self.client.post(
            f'/api/lessons/{lesson.id}/quiz/submit/',
            {'answers': {str(legacy_question.id): legacy_correct.id, str(lesson_question.id): correct_choice.id}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(LessonProgress.objects.filter(user=student, lesson=lesson).exists())

    def test_locked_and_unpublished_quiz_lessons_are_blocked_for_student(self):
        teacher = self.create_user('quiz-guard-teacher', User.IS_TEACHER)
        student = self.create_user('quiz-guard-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        unlocked = Lesson.objects.create(course=course, title='Unlocked quiz', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        locked = Lesson.objects.create(course=course, title='Locked quiz', type=Lesson.TYPE_QUIZ, content='', order=1, is_published=True)
        hidden = Lesson.objects.create(course=course, title='Hidden quiz', type=Lesson.TYPE_QUIZ, content='', order=2, is_published=False)
        self.create_question(course, text='Unlocked question', lesson=unlocked)
        self.create_question(course, text='Locked question', lesson=locked)
        self.create_question(course, text='Hidden question', lesson=hidden)

        self.authenticate(student)
        self.assertEqual(self.client.get(f'/api/lessons/{unlocked.id}/quiz/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(f'/api/lessons/{locked.id}/quiz/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(f'/api/lessons/{locked.id}/quiz/submit/', {'answers': {}}, format='json').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(f'/api/lessons/{hidden.id}/quiz/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(f'/api/lessons/{hidden.id}/quiz/submit/', {'answers': {}}, format='json').status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_quiz_lesson_removes_lesson_questions(self):
        teacher = self.create_user('delete-quiz-teacher', User.IS_TEACHER)
        student = self.create_user('delete-quiz-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        module = self.create_module(course, title='Quiz module', order=0)
        lesson = Lesson.objects.create(course=course, module=module, title='Quiz lesson', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        question, *_ = self.create_question(course, text='Quiz question', lesson=lesson)

        self.authenticate(teacher)
        delete_response = self.client.delete(f'/api/teacher/lessons/{lesson.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Question.objects.filter(id=question.id).exists())

        self.authenticate(student)
        outline_response = self.client.get(f'/api/courses/{course.id}/outline/')
        lesson_ids = [
            item['id']
            for module_payload in outline_response.data['modules']
            for item in module_payload.get('lessons', [])
        ]
        self.assertNotIn(lesson.id, lesson_ids)
        self.assertEqual(self.client.get(f'/api/lessons/{lesson.id}/quiz/').status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_legacy_question_does_not_affect_lesson_questions(self):
        teacher = self.create_user('legacy-delete-teacher', User.IS_TEACHER)
        student = self.create_user('legacy-delete-student', User.IS_STUDENT)
        course = self.create_course(author=teacher)
        lesson = Lesson.objects.create(course=course, title='Lesson quiz', type=Lesson.TYPE_QUIZ, content='', order=0, is_published=True)
        lesson_question, *_ = self.create_question(course, text='Lesson question survives', lesson=lesson)
        legacy_question, *_ = self.create_question(course, text='Legacy question removed', lesson=None)

        self.authenticate(teacher)
        response = self.client.delete(f'/api/teacher/questions/{legacy_question.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Question.objects.filter(id=legacy_question.id).exists())
        self.assertTrue(Question.objects.filter(id=lesson_question.id).exists())

        self.authenticate(student)
        lesson_quiz_response = self.client.get(f'/api/lessons/{lesson.id}/quiz/')
        self.assertEqual(lesson_quiz_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(lesson_quiz_response.data['questions']), 1)
        self.assertEqual(lesson_quiz_response.data['questions'][0]['id'], lesson_question.id)
