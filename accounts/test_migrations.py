from django.contrib.auth.hashers import check_password, make_password
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class IdentityMigrationTests(TransactionTestCase):
    def test_upgrade_keeps_ids_passwords_and_file_references(self):
        target = [('accounts', '0002_identity_and_permission_groups'), ('library', '0005_folder_uploader')]
        old_target = [('accounts', '0001_initial'), ('library', '0005_folder_uploader')]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            apps = executor.loader.project_state(old_target).apps
            User = apps.get_model('accounts', 'User')
            Folder = apps.get_model('library', 'Folder')
            File = apps.get_model('library', 'File')
            hashed = make_password('existing-secret')
            student = User.objects.create(username='fixture-student-a', password=hashed, role='student')
            teacher = User.objects.create(username='teacher', password=hashed, role='teacher')
            admin = User.objects.create(username='root', password=hashed, role='student', is_superuser=True)
            folder = Folder.objects.create(name='Keep', uploader=teacher)
            document = File.objects.create(name='Keep.bin', folder=folder, storage_key='keep', uploader=student, size=1, mime_type='')
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            apps = executor.loader.project_state(target).apps
            User = apps.get_model('accounts', 'User')
            File = apps.get_model('library', 'File')
            for original, key in [(student, 'student'), (teacher, 'teacher'), (admin, 'admin')]:
                updated = User.objects.select_related('permission_group').get(pk=original.pk)
                self.assertEqual(updated.username, original.username)
                self.assertEqual(updated.nickname, original.username)
                self.assertEqual(updated.password, hashed)
                self.assertTrue(check_password('existing-secret', updated.password))
                self.assertEqual(updated.permission_group.key, key)
            self.assertEqual(File.objects.get(pk=document.pk).uploader_id, student.pk)
        finally:
            MigrationExecutor(connection).migrate(target)
