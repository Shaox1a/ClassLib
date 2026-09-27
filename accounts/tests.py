from django.test import Client, TestCase
from django.urls import reverse

from .models import User


class AuthenticationPageTests(TestCase):
    def test_login_page_is_available(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '登录 ClassLib')

    def test_login_redirects_to_home(self):
        User.objects.create_user(username='student', password='safe-password')
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'student', 'password': 'safe-password'},
        )

        self.assertRedirects(response, reverse('library:home'))

    def test_disabled_user_cannot_log_in(self):
        User.objects.create_user(username='disabled', password='safe-password', is_active=False)
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'disabled', 'password': 'safe-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_ends_session(self):
        user = User.objects.create_user(username='student', password='safe-password')
        self.client.force_login(user)

        response = self.client.post(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_change_keeps_session_and_replaces_password(self):
        user = User.objects.create_user(username='student', password='old-password-123')
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'old-password-123',
            'new_password1': 'new-password-456',
            'new_password2': 'new-password-456',
        })

        self.assertRedirects(response, reverse('accounts:password_changed'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('new-password-456'))
        self.assertEqual(self.client.get(reverse('library:home')).status_code, 200)


class AccountManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', password='admin-password-123'
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='teacher-password-123', role=User.Role.TEACHER
        )

    def test_superuser_has_admin_role(self):
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_superuser_can_open_user_admin(self):
        self.client.force_login(self.admin)

        self.assertEqual(self.client.get(reverse('admin:accounts_user_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:accounts_user_add')).status_code, 200)

    def test_teacher_cannot_manage_accounts(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse('accounts:list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('accounts:create')).status_code, 403)
        self.assertEqual(self.client.post(reverse('accounts:status', args=[self.teacher.pk]), {
            'action': 'deactivate',
        }).status_code, 403)

    def test_admin_role_can_manage_accounts_without_staff_flag(self):
        manager = User.objects.create_user(
            username='manager', password='manager-password-123', role=User.Role.ADMIN
        )
        self.client.force_login(manager)

        self.assertEqual(self.client.get(reverse('accounts:list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:create')).status_code, 200)

    def test_admin_creates_student_and_teacher_only(self):
        self.client.force_login(self.admin)
        create_url = reverse('accounts:create')
        for username, role in [('student1', User.Role.STUDENT), ('teacher1', User.Role.TEACHER)]:
            response = self.client.post(create_url, {
                'username': username,
                'role': role,
                'password1': 'member-password-123',
                'password2': 'member-password-123',
            })
            self.assertRedirects(response, reverse('accounts:list'))
            self.assertEqual(User.objects.get(username=username).role, role)

        response = self.client.post(create_url, {
            'username': 'rogue',
            'role': User.Role.ADMIN,
            'password1': 'member-password-123',
            'password2': 'member-password-123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='rogue').exists())

    def test_admin_can_disable_and_enable_member(self):
        self.client.force_login(self.admin)
        status_url = reverse('accounts:status', args=[self.teacher.pk])
        self.assertRedirects(self.client.post(status_url, {'action': 'deactivate'}), reverse('accounts:list'))
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_active)

        self.client.logout()
        login_response = self.client.post(reverse('accounts:login'), {
            'username': 'teacher', 'password': 'teacher-password-123',
        })
        self.assertEqual(login_response.status_code, 200)

        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(status_url, {'action': 'activate'}), reverse('accounts:list'))
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)

    def test_admin_cannot_disable_admin_account(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('accounts:status', args=[self.admin.pk]), {
            'action': 'deactivate',
        })

        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_disabling_account_invalidates_existing_session(self):
        self.client.force_login(self.teacher)
        admin_client = Client()
        admin_client.force_login(self.admin)
        admin_client.post(reverse('accounts:status', args=[self.teacher.pk]), {
            'action': 'deactivate',
        })

        response = self.client.get(reverse('library:home'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))
