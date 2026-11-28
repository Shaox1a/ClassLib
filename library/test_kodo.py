from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from accounts.models import User
from .models import File, Folder


@override_settings(KODO_BUCKET='classlib-test', SUPABASE_URL='')
class KodoUploadTests(TestCase):
    def setUp(self):
        teacher = User.objects.create_user(username='teacher', role=User.Role.TEACHER)
        self.client.force_login(teacher)
        folder = Folder.objects.create(name='资料')
        self.begin = reverse('library:upload_begin', args=[folder.pk])
        self.finish = reverse('library:upload_finish', args=[folder.pk])

    @patch('library.kodo.client')
    def test_parts_and_idempotent_finish(self, get_client):
        s3 = get_client.return_value
        s3.create_multipart_upload.return_value = {'UploadId': 'upload'}
        s3.generate_presigned_url.return_value = 'https://example.org/signed-part'
        result = self.client.post(self.begin, {'name': '学生资料.bin', 'size': 6}).json()
        self.assertEqual(result['provider'], 'kodo')
        ticket = result['ticket']
        self.assertEqual(self.client.post(self.begin, {'ticket': ticket, 'part': 2}).status_code, 400)
        self.assertIn('url', self.client.post(self.begin, {'ticket': ticket, 'part': 1}).json())
        parts = s3.get_paginator.return_value.paginate
        parts.return_value = [{'Parts': [{'PartNumber': 1, 'Size': 5, 'ETag': 'etag'}]}]
        self.assertEqual(self.client.post(self.finish, {'ticket': ticket}).status_code, 400)
        s3.complete_multipart_upload.assert_not_called()
        self.assertFalse(File.objects.exists())
        parts.return_value[0]['Parts'][0]['Size'] = 6
        s3.head_object.return_value = {'ContentLength': 6}
        for _ in range(2):
            self.assertEqual(self.client.post(self.finish, {'ticket': ticket}).status_code, 200)
        s3.complete_multipart_upload.assert_called_once()
        self.assertEqual(File.objects.get().size, 6)

    @patch('library.kodo.client')
    def test_empty_file(self, get_client):
        ticket = self.client.post(self.begin, {'name': '空文件', 'size': 0}).json()['ticket']
        self.assertEqual(self.client.post(self.finish, {'ticket': ticket}).status_code, 200)
        get_client.return_value.create_multipart_upload.assert_not_called()
        get_client.return_value.put_object.assert_called_once_with(
            Bucket='classlib-test', Key=File.objects.get().storage_key, Body=b'')
