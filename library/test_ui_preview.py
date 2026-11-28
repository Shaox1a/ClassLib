from io import BytesIO
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from .models import File, Folder
from .services import preview_format


class HandoffUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user('teacher', password='test-password', role='teacher')
        cls.first = Folder.objects.create(name='First folder')
        cls.second = Folder.objects.create(name='Second folder')
        cls.image = File.objects.create(folder=cls.first, uploader=cls.teacher, name='photo.png',
                                        mime_type='image/png', storage_key='example-photo', size=1)

    def test_landing_hides_private_names_and_welcomes_once_after_login(self):
        landing = reverse('library:landing')
        response = self.client.get(landing)
        self.assertContains(response, '班级账号登录')
        self.assertNotContains(response, self.first.name)
        self.client.post(reverse('accounts:login'), {'username': 'teacher', 'password': 'test-password'})
        response = self.client.get(landing)
        self.assertContains(response, 'data-landing-welcome-scene')
        self.assertContains(response, self.first.name)
        self.assertNotContains(self.client.get(landing), 'data-landing-welcome-scene')

    def test_order_is_scoped_to_session_and_explicit_sort_wins(self):
        self.client.force_login(self.teacher)
        home = reverse('library:home')
        reorder = reverse('library:folder_reorder_set')
        first, second = self.first.pk, self.second.pk
        self.assertEqual(self.client.post(reorder, {'folders': str(first)}).status_code, 400)
        self.assertEqual(self.client.post(reorder, {'folders': f'{first},{second}'}).status_code, 200)
        self.assertEqual(list(self.client.get(home).context['folders']), [self.first, self.second])
        other = Client()
        other.force_login(self.teacher)
        self.assertEqual(list(other.get(home).context['folders']), [self.second, self.first])
        self.client.post(reverse('library:folder_reorder', args=[second]), {'direction': 'up'})
        self.assertEqual(list(self.client.get(home).context['folders']), [self.second, self.first])
        self.assertEqual(list(self.client.get(home, {'sort': 'name'}).context['folders']), [self.first, self.second])

    @patch('library.views.open_download')
    def test_thumbnail_and_inline_content_respect_existing_file_permissions(self, open_file):
        self.client.force_login(self.teacher)
        folder = reverse('library:folder', args=[self.first.pk])
        preview = reverse('library:file_preview', args=[self.image.pk])
        self.assertContains(self.client.get(folder), f'src="{preview}"')
        open_file.return_value = BytesIO(b'x')
        response = self.client.get(preview)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(b''.join(response.streaming_content), b'x')
        group = self.teacher.permission_group
        group.can_download = False
        group.save()
        self.assertNotContains(self.client.get(folder), f'src="{preview}"')
        self.assertEqual(self.client.get(preview).status_code, 403)
        open_file.assert_called_once()

    def test_preview_types(self):
        for name, mime, kind in [('x.pdf', '', 'pdf'), ('x.png', 'image/png', 'image'),
                                 ('x.mp3', 'audio/mpeg', 'audio'), ('x.mp4', 'video/mp4', 'video'),
                                 ('x.bin', 'application/octet-stream', 'none')]:
            with self.subTest(name=name):
                self.assertEqual(preview_format(name, mime)[0], kind)
        for name, mime in [('x.html', 'text/html'), ('x.svg', 'image/svg+xml'), ('x.js', 'text/javascript')]:
            self.assertEqual(preview_format(name, mime), ('text', 'text/plain; charset=utf-8'))
