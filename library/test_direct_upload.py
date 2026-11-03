from io import BytesIO
from unittest.mock import patch

from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from .direct_upload import SALT
from .models import File, Folder


@override_settings(SUPABASE_URL='https://example.supabase.co', SUPABASE_SERVICE_ROLE_KEY='sb_secret_test')
class DirectUploadTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', role=User.Role.TEACHER)
        self.student = User.objects.create_user(username='student')
        self.folder = Folder.objects.create(name='资料')
        self.begin_url = reverse('library:upload_begin', args=[self.folder.pk])
        self.finish_url = reverse('library:upload_finish', args=[self.folder.pk])
        self.client.force_login(self.teacher)

    def ticket(self, name='notes.txt', size=5, **extra):
        data = {'user': self.teacher.pk, 'folder': self.folder.pk,
                'key': 'test-key.txt', 'name': name, 'size': size}
        data.update(extra)
        return signing.dumps(data, salt=SALT)

    @patch('library.storage.signed_upload', return_value='https://example.supabase.co/upload?token=limited')
    def test_only_teacher_can_get_upload_link(self, sign):
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.begin_url, {'name': 'a.txt', 'size': 5}).status_code, 403)
        sign.assert_not_called()
        self.client.force_login(self.teacher)
        result = self.client.post(self.begin_url, {'name': 'a.txt', 'size': 5})
        self.assertEqual(result.status_code, 200)
        payload = signing.loads(result.json()['ticket'], salt=SALT)
        self.assertEqual(payload['user'], self.teacher.pk)
        self.assertNotIn('sb_secret_test', result.content.decode())

    @patch('library.storage.open_file')
    def test_ticket_cannot_be_forged_or_used_by_another_user(self, open_file):
        for ticket in ['forged', self.ticket(user=self.student.pk), self.ticket(folder=999)]:
            result = self.client.post(self.finish_url, {'ticket': ticket})
            self.assertEqual(result.status_code, 400)
        open_file.assert_not_called()

    @patch('library.storage.delete')
    @patch('library.storage.save', side_effect=lambda key, uploaded: key)
    @patch('library.storage.open_file')
    def test_large_upload_validated_and_retry_does_not_duplicate(self, open_file, save, delete):
        content = b'a' * (5 * 1024 * 1024)
        open_file.return_value = BytesIO(content)
        ticket = self.ticket(size=len(content))
        response = self.client.post(self.finish_url, {'ticket': ticket})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(File.objects.get().size, len(content))
        self.assertEqual(save.call_args.args[0], 'test-key.txt')
        delete.assert_called_once_with('pending/test-key.txt')
        self.assertEqual(self.client.post(self.finish_url, {'ticket': ticket}).json(), response.json())
        self.assertEqual(File.objects.count(), 1)
        self.assertEqual(save.call_count, 1)

    @patch('library.storage.delete')
    @patch('library.storage.save')
    @patch('library.storage.open_file', side_effect=lambda key: BytesIO(b'hello'))
    def test_mismatched_size_and_disguised_content_are_rejected(self, open_file, save, delete):
        for ticket in [self.ticket(size=100), self.ticket(name='fake.pdf')]:
            self.assertEqual(self.client.post(self.finish_url, {'ticket': ticket}).status_code, 400)
        self.assertFalse(File.objects.exists())
        save.assert_not_called()

    @patch('library.storage.signed_download', return_value='https://example.supabase.co/object/sign/file?token=short')
    def test_download_authentication_precedes_signing(self, sign):
        document = File.objects.create(folder=self.folder, name='notes.txt', storage_key='test.txt',
                                       size=5, mime_type='text/plain', uploader=self.teacher)
        url = reverse('library:file_download', args=[document.pk])
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        sign.assert_not_called()
        self.client.force_login(self.student)
        result = self.client.get(url)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result['Cache-Control'], 'private, no-store')
        sign.assert_called_once_with('test.txt', 'notes.txt')
