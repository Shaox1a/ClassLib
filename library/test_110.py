from tempfile import TemporaryDirectory
from uuid import uuid4
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from .models import File, Folder

class UpgradeTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix='classlib-test-')
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(PRIVATE_FILE_ROOT=self.directory.name)
        self.override.enable(); self.addCleanup(self.override.disable)
        self.user = User.objects.create_user(username='teacher', password='secret', role=User.Role.TEACHER)
        self.client.force_login(self.user)
        self.folder = Folder.objects.create(name='Test')

    def test_empty_arbitrary_and_large_local_streamed_uploads(self):
        for name, data in [('empty', b''), ('script.exe', b'anything'), ('fake.pdf', b'not pdf')]:
            result = self.client.post(f'/folder/{self.folder.pk}/upload/', {'upload': SimpleUploadedFile(name,data)})
            self.assertEqual(result.status_code,302)
        self.assertEqual(File.objects.count(),3)
        self.assertEqual(File.objects.get(name='empty').size,0)

    def test_queue_upload_retry_and_duplicate_names(self):
        url=f'/folder/{self.folder.pk}/upload/'
        ident=str(uuid4())
        for _ in range(2):
            result=self.client.post(url,{'upload': SimpleUploadedFile('file.bin',b'abc')},HTTP_X_UPLOAD_QUEUE='1',HTTP_X_UPLOAD_ID=ident)
            self.assertEqual(result.status_code,200)
        self.assertEqual(File.objects.count(),1)
        result=self.client.post(url,{'upload': SimpleUploadedFile('file.bin',b'abc')},HTTP_X_UPLOAD_QUEUE='1',HTTP_X_UPLOAD_ID=str(uuid4()))
        self.assertEqual(result.status_code,400)

    def test_details_templates_and_updated_date(self):
        original=self.folder.updated_at
        self.client.post(f'/folder/{self.folder.pk}/rename/',{'name':'New'})
        self.folder.refresh_from_db(); self.assertGreater(self.folder.updated_at,original)
        for url in ['/',f'/folder/{self.folder.pk}/','/search/?q=New']:
            response=self.client.get(url)
            self.assertContains(response,'修改日期')
            self.assertContains(response,'data-details-view')

    @override_settings(SUPABASE_URL='https://example.supabase.co')
    @patch('library.storage.signed_upload',return_value='https://example.supabase.co/upload?token=limited')
    def test_cloud_allows_gib_and_zero(self,sign):
        for size in [0, 1024**3, 3*1024**3]:
            result=self.client.post(f'/folder/{self.folder.pk}/upload/begin/',{'name':'file.exe','size':size})
            self.assertEqual(result.status_code,200)
            self.assertTrue(result.json()['endpoint'].endswith('/resumable/sign'))
            self.assertNotIn('secret', result.content.decode())

    def test_login_error_never_echoes_password_and_next_is_safe(self):
        self.client.logout()
        result=self.client.post('/login/',{'username':'teacher','password':'wrong-password'},HTTP_X_LOGIN_FORM='1')
        self.assertEqual(result.status_code,400)
        self.assertNotIn('wrong-password',result.content.decode())
        result=self.client.post('/login/?next=https://evil.example',{'username':'teacher','password':'secret'},HTTP_X_LOGIN_FORM='1')
        self.assertEqual(result.json()['redirect'],'/')
