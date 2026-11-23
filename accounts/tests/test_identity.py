from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import authenticate
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.urls import reverse

from library.models import File, Folder
from accounts.management.commands.sync_accounts import read_roster
from accounts.models import PermissionGroup, User


class IdentityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='fixture-student-a', nickname='同学甲', password='old-secret-123')

    def test_login_by_id_and_nickname(self):
        for identity in ('fixture-student-a', '同学甲'):
            self.assertEqual(authenticate(username=identity, password='old-secret-123'), self.user)
        self.assertIsNone(authenticate(username='同学甲', password='wrong'))

    def test_profile_change_nickname_preserves_id_password_and_file_ownership(self):
        folder = Folder.objects.create(name='Owned', uploader=self.user)
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile'), {'nickname': '新昵称', 'username': 'hacked', 'permission_group': '0'})
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_id, 'fixture-student-a')
        self.assertEqual(self.user.nickname, '新昵称')
        self.assertEqual(self.user.role, 'student')
        self.assertTrue(self.user.check_password('old-secret-123'))
        folder.refresh_from_db()
        self.assertEqual(folder.uploader_id, self.user.pk)
        self.assertEqual(authenticate(username='新昵称', password='old-secret-123'), self.user)
        self.assertIsNone(authenticate(username='同学甲', password='old-secret-123'))

    def test_id_is_immutable_in_model(self):
        self.user.username = 'new-id'
        with self.assertRaises(ValidationError):
            self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_id, 'fixture-student-a')

    def test_nickname_and_id_cannot_collide_with_other_accounts(self):
        other = User.objects.create_user(username='fixture-student-b', nickname='同学乙', password='other-secret')
        self.client.force_login(self.user)
        for nickname in (other.nickname, other.username, '   '):
            response = self.client.post(reverse('accounts:profile'), {'nickname': nickname})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
        with self.assertRaises(ValidationError):
            User.objects.create_user(username='同学甲', nickname='其他人', password='secret')

    def test_password_change_requires_current_password_and_retains_session(self):
        self.client.force_login(self.user)
        data = {'nickname': self.user.nickname, 'new_password1': 'new-secret-456', 'new_password2': 'new-secret-456'}
        response = self.client.post(reverse('accounts:profile'), {**data, 'current_password': 'wrong'})
        self.assertContains(response, '当前密码不正确')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('old-secret-123'))
        self.assertRedirects(self.client.post(reverse('accounts:profile'), {**data, 'current_password': 'old-secret-123'}), reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-secret-456'))
        self.assertIsNone(authenticate(username='fixture-student-a', password='old-secret-123'))
        self.assertEqual(self.client.get(reverse('library:home')).status_code, 200)

    def test_profile_never_exposes_original_password_or_hash(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        for text in ('ID', '昵称', '密码', '权限组'):
            self.assertContains(response, text)
        self.assertNotContains(response, '<dt>昵称</dt>')
        self.assertNotContains(response, '<dt>密码</dt>')
        self.assertNotContains(response, 'old-secret-123')
        self.assertNotContains(response, self.user.password)
        self.assertNotContains(response, 'name="username"')

    def test_failed_json_login_keeps_generic_error_without_echoing_password(self):
        response = self.client.post(reverse('accounts:login'), {'username': '同学甲', 'password': 'wrong-keep'}, HTTP_X_LOGIN_FORM='1')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('wrong-keep', response.content.decode())

    def test_login_ignores_external_redirect(self):
        response = self.client.post(
            reverse('accounts:login') + '?next=https://example.invalid/',
            {'username': self.user.username, 'password': 'old-secret-123'},
            HTTP_X_LOGIN_FORM='1',
        )
        self.assertEqual(response.json()['redirect'], '/')


class AdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='root', nickname='管理员', password='root-secret')
        self.student = User.objects.create_user(username='student', nickname='学生甲', password='member-secret')
        self.teacher = User.objects.create_user(username='teacher', nickname='教师甲', role='teacher', password='teacher-secret')
        self.client.force_login(self.admin)

    def test_edit_all_mutable_account_fields_and_never_id_or_hash(self):
        url = reverse('accounts:edit', args=[self.student.pk])
        response = self.client.get(url)
        self.assertNotContains(response, self.student.password)
        self.assertNotContains(response, 'member-secret')
        self.assertNotContains(response, 'name="username"')
        data = {'username': 'hacked', 'nickname': '新老师', 'permission_group': self.teacher.permission_group_id,
                'is_active': True, 'new_password1': 'reset-secret-456', 'new_password2': 'reset-secret-456'}
        self.assertRedirects(self.client.post(url, data), reverse('accounts:list'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.account_id, 'student')
        self.assertEqual(self.student.nickname, '新老师')
        self.assertEqual(self.student.role, 'teacher')
        self.assertTrue(self.student.check_password('reset-secret-456'))

    def test_create_default_password_is_id_and_any_group_is_allowed(self):
        self.assertRedirects(self.client.post(reverse('accounts:create'), {
            'username': 'new-manager', 'nickname': '新管理员', 'permission_group': self.admin.permission_group_id,
        }), reverse('accounts:list'))
        user = User.objects.get(username='new-manager')
        self.assertTrue(user.check_password('new-manager'))
        self.assertEqual(user.role, 'admin')

    def test_explicit_new_password_is_validated_against_submitted_id(self):
        response = self.client.post(reverse('accounts:create'), {
            'username': 'long-unique-id', 'nickname': '新人', 'permission_group': self.student.permission_group_id,
            'new_password1': 'long-unique-id', 'new_password2': 'long-unique-id',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors.get('new_password1'))
        self.assertFalse(User.objects.filter(username='long-unique-id').exists())

    def test_bulk_reset_is_limited_to_selection_and_invalidates_old_session(self):
        member_client = Client()
        member_client.force_login(self.student)
        self.assertRedirects(self.client.post(reverse('accounts:bulk'), {
            'selected': [self.student.pk, self.teacher.pk], 'action': 'reset',
        }), reverse('accounts:list'))
        for user in (self.student, self.teacher):
            user.refresh_from_db()
            self.assertTrue(user.check_password(user.account_id))
            self.assertNotEqual(user.password, user.account_id)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('root-secret'))
        self.assertEqual(member_client.get(reverse('library:home')).status_code, 302)

    def test_bulk_move_and_immediate_permission_change_in_existing_session(self):
        member_client = Client()
        member_client.force_login(self.teacher)
        folder = Folder.objects.create(name='A')
        url = reverse('library:file_upload', args=[folder.pk])
        self.assertEqual(member_client.get(url).status_code, 200)
        self.assertRedirects(self.client.post(reverse('accounts:bulk'), {
            'selected': [self.teacher.pk], 'action': 'move', 'permission_group': self.student.permission_group_id,
        }), reverse('accounts:list'))
        self.assertEqual(member_client.get(url).status_code, 403)

    def test_bulk_rejects_empty_or_invalid_selection_atomically(self):
        for data in ({'action': 'reset'}, {'selected': [self.student.pk, 999999], 'action': 'reset'},
                     {'selected': [self.student.pk], 'action': 'move'},
                     {'selected': [self.student.pk], 'action': 'move', 'permission_group': 999999}):
            response = self.client.post(reverse('accounts:bulk'), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['bulk_form'].errors)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('member-secret'))

    def test_cannot_remove_last_administrator_by_edit_or_bulk(self):
        response = self.client.post(reverse('accounts:edit', args=[self.admin.pk]), {
            'nickname': '管理员', 'permission_group': self.student.permission_group_id, 'is_active': True,
        })
        self.assertContains(response, '至少保留一个')
        response = self.client.post(reverse('accounts:bulk'), {
            'selected': [self.admin.pk, self.teacher.pk], 'action': 'move', 'permission_group': self.student.permission_group_id,
        })
        self.assertContains(response, '至少保留一个')
        self.admin.refresh_from_db()
        self.teacher.refresh_from_db()
        self.assertEqual(self.admin.role, 'admin')
        self.assertEqual(self.teacher.role, 'teacher')

    def test_admin_can_edit_other_admin_including_deactivate(self):
        other = User.objects.create_user(username='other-admin', nickname='其他管理员', role='admin')
        self.assertRedirects(self.client.post(reverse('accounts:edit', args=[other.pk]), {
            'nickname': '已停用管理员', 'permission_group': self.student.permission_group_id,
        }), reverse('accounts:list'))
        other.refresh_from_db()
        self.assertFalse(other.is_active)
        self.assertEqual(other.role, 'student')

    def test_non_admin_cannot_forge_management_requests(self):
        self.client.force_login(self.student)
        requests = [
            ('get', reverse('accounts:list'), {}), ('get', reverse('accounts:groups'), {}),
            ('post', reverse('accounts:edit', args=[self.admin.pk]), {'nickname': '伪造'}),
            ('post', reverse('accounts:bulk'), {'selected': [self.admin.pk], 'action': 'reset'}),
            ('post', reverse('accounts:group_create'), {'name': '伪造组', 'can_manage_accounts': True}),
            ('post', reverse('accounts:group_delete', args=[self.admin.permission_group_id]), {}),
        ]
        for method, url, data in requests:
            self.assertEqual(getattr(self.client, method)(url, data).status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('root-secret'))

    def test_csrf_required_for_bulk(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse('accounts:bulk'), {'selected': [self.student.pk], 'action': 'reset'}).status_code, 403)


class GroupEditingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='root', password='root-secret')
        self.student = User.objects.create_user(username='student', password='student-secret')
        self.client.force_login(self.admin)

    def test_add_edit_and_delete_group_with_member_transfer(self):
        self.assertRedirects(self.client.post(reverse('accounts:group_create'), {'name': '投稿者', 'can_view': True, 'can_upload': True}), reverse('accounts:groups'))
        group = PermissionGroup.objects.get(name='投稿者')
        self.student.permission_group = group
        self.student.save()
        member_client = Client()
        member_client.force_login(self.student)
        folder = Folder.objects.create(name='A')
        response = member_client.get(reverse('library:folder', args=[folder.pk]))
        self.assertContains(response, '上传文件')
        self.assertNotContains(response, '新建子文件夹')
        self.assertRedirects(self.client.post(reverse('accounts:group_edit', args=[group.pk]), {'name': '只读', 'can_view': True}), reverse('accounts:groups'))
        self.assertEqual(member_client.get(reverse('library:file_upload', args=[folder.pk])).status_code, 403)
        destination = self.admin.permission_group
        response = self.client.post(reverse('accounts:group_delete', args=[group.pk]), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PermissionGroup.objects.filter(pk=group.pk).exists())
        self.assertRedirects(self.client.post(reverse('accounts:group_delete', args=[group.pk]), {'replacement': destination.pk}), reverse('accounts:groups'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.permission_group, destination)
        self.assertFalse(PermissionGroup.objects.filter(pk=group.pk).exists())

    def test_last_administrator_group_cannot_lose_management_rights_or_be_deleted(self):
        group = self.admin.permission_group
        response = self.client.post(reverse('accounts:group_edit', args=[group.pk]), {'name': 'No admin', 'can_view': True})
        self.assertContains(response, '至少保留一个')
        group.refresh_from_db()
        self.assertTrue(group.can_manage_groups)
        response = self.client.post(reverse('accounts:group_delete', args=[group.pk]), {'replacement': self.student.permission_group_id})
        self.assertContains(response, '至少保留一个')
        self.assertTrue(PermissionGroup.objects.filter(pk=group.pk).exists())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.permission_group_id, group.pk)

    def test_group_names_are_unique_and_empty_groups_can_be_deleted(self):
        response = self.client.post(reverse('accounts:group_create'), {'name': self.admin.permission_group.name})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        empty = PermissionGroup.objects.create(name='空组')
        self.assertRedirects(self.client.post(reverse('accounts:group_delete', args=[empty.pk]), {}), reverse('accounts:groups'))

    def test_superuser_flag_does_not_bypass_current_permission_group(self):
        self.admin.permission_group = self.student.permission_group
        self.admin.save()
        self.assertEqual(self.client.get(reverse('accounts:list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('accounts:groups')).status_code, 403)
        self.assertEqual(self.client.get(reverse('library:folder_create_root')).status_code, 403)

    def test_account_and_group_permissions_are_independent_and_login_without_view_works(self):
        group = PermissionGroup.objects.create(name='账户维护', can_manage_accounts=True)
        self.student.permission_group = group
        self.student.save()
        self.client.logout()
        self.assertRedirects(self.client.post(reverse('accounts:login'), {'username': 'student', 'password': 'student-secret'}), reverse('accounts:profile'))
        self.assertEqual(self.client.get(reverse('accounts:list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('accounts:groups')).status_code, 403)


ROSTER = '''### 本地端账户，格式为id+昵称+密码：
root 测试管理员 fixture-admin-pass
student 测试学生 fixture-student-pass
teacher 测试教师 fixture-teacher-pass
### 部署端账户，格式为id+昵称+密码：
#### 学生账户id：
fixture-student-a 同学甲 fixture-student-a
#### 管理员账户id：
root 测试管理员 fixture-admin-pass
'''


class RosterTests(TestCase):
    def test_replace_local_preserves_ids_ownership_hashes_and_invalidates_sessions(self):
        root = User.objects.create_superuser(username='root', password='old-secret')
        folder = Folder.objects.create(name='Keep', uploader=root)
        User.objects.create_user(username='obsolete', password='secret')
        self.client.force_login(root)
        output = StringIO()
        with patch.object(Path, 'read_text', return_value=ROSTER):
            call_command('sync_accounts', 'unused.md', environment='local', replace=True, stdout=output)
        self.assertEqual(set(User.objects.values_list('username', flat=True)), {'root', 'student', 'teacher'})
        self.assertEqual(User.objects.get(username='root').pk, root.pk)
        folder.refresh_from_db()
        self.assertEqual(folder.uploader_id, root.pk)
        for user in User.objects.all():
            self.assertTrue(user.check_password(f'fixture-{user.role}-pass'))
        self.assertFalse(Session.objects.exists())
        self.assertNotIn('student student', output.getvalue())

    def test_replacement_rolls_back_when_obsolete_account_owns_protected_files(self):
        old = User.objects.create_user(username='obsolete', password='old-secret')
        folder = Folder.objects.create(name='Keep')
        File.objects.create(name='Keep.bin', folder=folder, storage_key='keep', size=1, mime_type='', uploader=old)
        with patch.object(Path, 'read_text', return_value=ROSTER):
            with self.assertRaises(CommandError):
                call_command('sync_accounts', 'unused.md', environment='local', replace=True, stdout=StringIO())
        self.assertEqual(User.objects.count(), 1)
        old.refresh_from_db()
        self.assertTrue(old.check_password('old-secret'))

    def test_dry_run_and_missing_replace_do_not_change_accounts(self):
        with patch.object(Path, 'read_text', return_value=ROSTER):
            call_command('sync_accounts', 'unused.md', environment='local', dry_run=True, stdout=StringIO())
            with self.assertRaises(CommandError):
                call_command('sync_accounts', 'unused.md', environment='local', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_rejects_missing_admin_duplicate_nickname_and_cross_identity_collision(self):
        for text in (ROSTER.replace('root 测试管理员 fixture-admin-pass\n', ''),
                     ROSTER.replace('student 测试学生 fixture-student-pass', 'student 测试管理员 fixture-student-pass'),
                     ROSTER.replace('student 测试学生 fixture-student-pass', 'student root fixture-student-pass')):
            with patch.object(Path, 'read_text', return_value=text):
                with self.assertRaises(CommandError):
                    read_roster(Path('unused'), 'local')

    def test_production_parser_uses_only_production_section_and_local_import_refuses_postgres(self):
        with patch.object(Path, 'read_text', return_value=ROSTER):
            rows = read_roster(Path('unused'), 'production')
            self.assertEqual({row[0] for row in rows}, {'root', 'fixture-student-a'})
        with patch('accounts.management.commands.sync_accounts.settings') as command_settings:
            command_settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}
            with self.assertRaises(CommandError):
                call_command('sync_accounts', 'unused', environment='local', replace=True, stdout=StringIO())
