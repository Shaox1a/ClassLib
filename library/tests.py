from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User

from .models import File, Folder, Tag
from .permissions import has_permission


class LibraryTests(TestCase):
    def setUp(self):
        self.storage_dir = TemporaryDirectory(prefix='classlib-test-', dir=settings.BASE_DIR)
        self.addCleanup(self.cleanup_storage)
        storage_settings = override_settings(PRIVATE_FILE_ROOT=self.storage_dir.name)
        storage_settings.enable()
        self.addCleanup(storage_settings.disable)

        self.student = User.objects.create_user(username='student', password='student-password')
        self.teacher = User.objects.create_user(
            username='teacher', password='teacher-password', role=User.Role.TEACHER
        )
        self.root = Folder.objects.create(name='数学')
        self.child = Folder.objects.create(name='函数', parent=self.root)

    def cleanup_storage(self):
        root = Path(settings.BASE_DIR).resolve()
        target = Path(self.storage_dir.name).resolve()
        if root not in target.parents or not target.name.startswith('classlib-test-'):
            raise AssertionError('Unexpected test storage path')
        self.storage_dir.cleanup()

    def upload_text(self, folder, name='notes.txt', content=b'hello class'):
        return self.client.post(
            reverse('library:file_upload', args=[folder.pk]),
            {'upload': SimpleUploadedFile(name, content, content_type='text/plain')},
        )

    def test_anonymous_visitors_are_redirected_from_library_and_download(self):
        self.client.force_login(self.teacher)
        self.upload_text(self.child)
        document = File.objects.get()
        self.client.logout()

        for url in (
            reverse('library:home'),
            reverse('library:folder', args=[self.child.pk]),
            reverse('library:file', args=[document.pk]),
            reverse('library:file_download', args=[document.pk]),
            reverse('library:search'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('accounts:login')))
        self.assertEqual(self.client.get(f'/private_files/{document.storage_key}').status_code, 404)

    def test_student_can_browse_and_download_but_cannot_manage(self):
        self.client.force_login(self.teacher)
        self.upload_text(self.child)
        document = File.objects.get()
        self.client.force_login(self.student)

        self.assertContains(self.client.get(reverse('library:home')), '数学')
        folder_page = self.client.get(reverse('library:folder', args=[self.child.pk]))
        self.assertContains(folder_page, 'notes.txt')
        self.assertNotContains(folder_page, '上传文件')
        self.assertContains(self.client.get(reverse('library:file', args=[document.pk])), '下载文件')
        download = self.client.get(reverse('library:file_download', args=[document.pk]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), b'hello class')
        self.assertIn('attachment', download['Content-Disposition'])
        self.assertEqual(download['Cache-Control'], 'private, no-store')
        download.close()

        for url in (
            reverse('library:folder_create_root'),
            reverse('library:folder_create_child', args=[self.root.pk]),
            reverse('library:folder_rename', args=[self.root.pk]),
            reverse('library:folder_move', args=[self.root.pk]),
            reverse('library:folder_delete', args=[self.root.pk]),
            reverse('library:file_upload', args=[self.child.pk]),
            reverse('library:file_rename', args=[document.pk]),
            reverse('library:file_move', args=[document.pk]),
            reverse('library:file_delete', args=[document.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_teacher_creates_renames_moves_and_deletes_folders(self):
        self.client.force_login(self.teacher)
        child_response = self.client.post(
            reverse('library:folder_create_child', args=[self.root.pk]), {'name': '几何'}
        )
        new_child = Folder.objects.get(name='几何')
        self.assertRedirects(child_response, reverse('library:folder', args=[new_child.pk]))
        self.assertEqual(new_child.parent, self.root)
        self.assertRedirects(
            self.client.post(reverse('library:folder_create_root'), {'name': '英语'}),
            reverse('library:folder', args=[Folder.objects.get(name='英语').pk]),
        )
        english = Folder.objects.get(name='英语')
        self.assertRedirects(
            self.client.post(reverse('library:folder_rename', args=[english.pk]), {'name': '英语资料'}),
            reverse('library:folder', args=[english.pk]),
        )
        self.assertRedirects(
            self.client.post(reverse('library:folder_move', args=[english.pk]), {'parent': self.root.pk}),
            reverse('library:folder', args=[english.pk]),
        )
        english.refresh_from_db()
        self.assertEqual(english.parent, self.root)
        self.assertEqual(english.name, '英语资料')
        self.assertContains(self.client.get(reverse('library:folder', args=[self.root.pk])), '英语资料')
        self.assertRedirects(
            self.client.post(reverse('library:folder_delete', args=[english.pk])),
            reverse('library:folder', args=[self.root.pk]),
        )
        self.assertFalse(Folder.objects.filter(pk=english.pk).exists())

    def test_folder_cycle_and_duplicate_names_are_rejected(self):
        self.client.force_login(self.teacher)
        response = self.client.post(reverse('library:folder_move', args=[self.root.pk]), {
            'parent': self.child.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.root.refresh_from_db()
        self.assertIsNone(self.root.parent)

        response = self.client.post(reverse('library:folder_create_root'), {'name': '数学'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Folder.objects.filter(name='数学', parent__isnull=True).count(), 1)

    def test_file_upload_rename_move_and_delete(self):
        self.client.force_login(self.teacher)
        upload_response = self.upload_text(self.child)
        document = File.objects.get()
        self.assertRedirects(upload_response, reverse('library:file', args=[document.pk]))
        self.assertEqual(document.uploader, self.teacher)
        self.assertEqual(document.size, len(b'hello class'))
        self.assertTrue(Path(self.storage_dir.name, document.storage_key).is_file())

        self.assertRedirects(
            self.client.post(reverse('library:file_rename', args=[document.pk]), {'name': 'lesson.txt'}),
            reverse('library:file', args=[document.pk]),
        )
        self.assertRedirects(
            self.client.post(reverse('library:file_move', args=[document.pk]), {'folder': self.root.pk}),
            reverse('library:file', args=[document.pk]),
        )
        document.refresh_from_db()
        self.assertEqual((document.name, document.folder), ('lesson.txt', self.root))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('library:file_delete', args=[document.pk]))
        self.assertRedirects(response, reverse('library:folder', args=[self.root.pk]))
        self.assertFalse(File.objects.filter(pk=document.pk).exists())
        self.assertFalse(Path(self.storage_dir.name, document.storage_key).exists())

    def test_deleting_folder_cleans_descendant_files(self):
        self.client.force_login(self.teacher)
        self.upload_text(self.child)
        document = File.objects.get()
        stored_path = Path(self.storage_dir.name, document.storage_key)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('library:folder_delete', args=[self.root.pk]))
        self.assertRedirects(response, reverse('library:home'))
        self.assertFalse(Folder.objects.filter(pk__in=[self.root.pk, self.child.pk]).exists())
        self.assertFalse(File.objects.filter(pk=document.pk).exists())
        self.assertFalse(stored_path.exists())

    def test_invalid_uploads_and_duplicate_names_are_rejected(self):
        self.client.force_login(self.teacher)
        response = self.upload_text(self.child, 'fake.pdf', b'not a pdf')
        self.assertEqual(response.status_code, 200)
        response = self.upload_text(self.child, 'script.exe', b'MZ')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(File.objects.exists())

        self.upload_text(self.child)
        duplicate = self.upload_text(self.child)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(File.objects.count(), 1)

    def test_pdf_and_docx_content_are_accepted(self):
        self.client.force_login(self.teacher)
        pdf = SimpleUploadedFile('handout.pdf', b'%PDF-1.4\nexample', content_type='application/pdf')
        response = self.client.post(reverse('library:file_upload', args=[self.child.pk]), {
            'upload': pdf,
        })
        self.assertEqual(response.status_code, 302)

        content = BytesIO()
        with ZipFile(content, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', '<document/>')
        docx = SimpleUploadedFile(
            'handout.docx', content.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response = self.client.post(reverse('library:file_upload', args=[self.child.pk]), {
            'upload': docx,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(File.objects.count(), 2)

    def test_rename_extension_and_move_collision_are_rejected(self):
        self.client.force_login(self.teacher)
        self.upload_text(self.child)
        document = File.objects.get()
        self.upload_text(self.root)

        rename_response = self.client.post(reverse('library:file_rename', args=[document.pk]), {
            'name': 'notes.pdf',
        })
        move_response = self.client.post(reverse('library:file_move', args=[document.pk]), {
            'folder': self.root.pk,
        })

        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(move_response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.name, 'notes.txt')
        self.assertEqual(document.folder, self.child)

    @override_settings(MAX_UPLOAD_SIZE=4)
    def test_upload_size_limit_is_enforced(self):
        self.client.force_login(self.teacher)
        response = self.upload_text(self.child, content=b'12345')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(File.objects.exists())

    def test_missing_file_content_returns_404(self):
        self.client.force_login(self.teacher)
        self.upload_text(self.child)
        document = File.objects.get()
        Path(self.storage_dir.name, document.storage_key).unlink()

        self.assertEqual(self.client.get(reverse('library:file_download', args=[document.pk])).status_code, 404)

    def test_search_page_keeps_query(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('library:search'), {'q': '函数'})

        self.assertContains(response, '函数')


class TagAndSearchTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student', password='student-password')
        self.teacher = User.objects.create_user(
            username='teacher', password='teacher-password', role=User.Role.TEACHER
        )
        self.admin_user = User.objects.create_superuser(
            username='admin', password='admin-password'
        )
        self.math = Folder.objects.create(name='数学')
        self.functions = Folder.objects.create(name='函数', parent=self.math)
        self.english = Folder.objects.create(name='英语')
        self.math_file = File.objects.create(
            name='导数练习.pdf', folder=self.functions, storage_key='math.pdf',
            size=10, mime_type='application/pdf', uploader=self.teacher,
        )
        self.english_file = File.objects.create(
            name='阅读材料.pdf', folder=self.english, storage_key='english.pdf',
            size=10, mime_type='application/pdf', uploader=self.teacher,
        )
        self.review = Tag.objects.create(name='期中复习')
        self.math_file.tags.add(self.review)

    def result_file_ids(self, response):
        return {document.pk for document in response.context['file_page']}

    def test_permission_matrix_and_student_tag_management_denial(self):
        self.assertFalse(has_permission(AnonymousUser(), 'view'))
        self.assertTrue(has_permission(self.student, 'view'))
        self.assertTrue(has_permission(self.student, 'download'))
        self.assertFalse(has_permission(self.student, 'upload'))
        self.assertFalse(has_permission(self.student, 'manage'))
        for action in ('view', 'download', 'upload', 'manage'):
            self.assertTrue(has_permission(self.teacher, action))
            self.assertTrue(has_permission(self.admin_user, action))

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('library:tags')).status_code, 200)
        for url in (
            reverse('library:tag_create'),
            reverse('library:tag_rename', args=[self.review.pk]),
            reverse('library:tag_delete', args=[self.review.pk]),
            reverse('library:file_tags', args=[self.math_file.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)

        self.client.logout()
        for url in (reverse('library:tags'), reverse('library:search')):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_search_finds_file_name_folder_name_and_tag_name(self):
        self.client.force_login(self.student)
        by_file = self.client.get(reverse('library:search'), {'q': '导数'})
        by_folder = self.client.get(reverse('library:search'), {'q': '数学'})
        by_child_folder = self.client.get(reverse('library:search'), {'q': '函数'})
        by_tag = self.client.get(reverse('library:search'), {'q': '期中'})

        for response in (by_file, by_folder, by_child_folder, by_tag):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.result_file_ids(response), {self.math_file.pk})
        self.assertContains(by_folder, '数学')
        self.assertContains(by_child_folder, '函数')
        self.assertContains(by_child_folder, '数学 / 函数')

    def test_subject_and_tag_filters_can_be_combined(self):
        self.client.force_login(self.student)
        subject_result = self.client.get(reverse('library:search'), {'subject': self.math.pk})
        tag_result = self.client.get(reverse('library:search'), {'tag': self.review.pk})
        combined = self.client.get(reverse('library:search'), {
            'subject': self.english.pk, 'tag': self.review.pk,
        })

        self.assertEqual(self.result_file_ids(subject_result), {self.math_file.pk})
        self.assertEqual(self.result_file_ids(tag_result), {self.math_file.pk})
        self.assertEqual(self.result_file_ids(combined), set())
        self.assertContains(combined, '没有找到匹配的资料')

    def test_teacher_assigns_multiple_tags_and_can_remove_them(self):
        self.client.force_login(self.teacher)
        extra = Tag.objects.create(name='练习题')
        edit_url = reverse('library:file_tags', args=[self.math_file.pk])

        response = self.client.post(edit_url, {'tags': [self.review.pk, extra.pk]})
        self.assertRedirects(response, reverse('library:file', args=[self.math_file.pk]))
        self.assertEqual(set(self.math_file.tags.values_list('pk', flat=True)), {
            self.review.pk, extra.pk,
        })
        self.assertContains(self.client.get(reverse('library:file', args=[self.math_file.pk])), '#练习题')

        self.client.post(edit_url, {})
        self.assertFalse(self.math_file.tags.exists())
        self.assertTrue(File.objects.filter(pk=self.math_file.pk).exists())

    def test_tag_creation_rename_and_delete_keep_file(self):
        self.client.force_login(self.teacher)
        create_response = self.client.post(reverse('library:tag_create'), {'name': '#Review'})
        self.assertRedirects(create_response, reverse('library:tags'))
        tag = Tag.objects.get(name='Review')

        duplicate = self.client.post(reverse('library:tag_create'), {'name': '#review'})
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(Tag.objects.filter(name__iexact='review').count(), 1)

        self.assertRedirects(
            self.client.post(reverse('library:tag_rename', args=[tag.pk]), {'name': '考试'}),
            reverse('library:tags'),
        )
        tag.refresh_from_db()
        self.assertEqual(tag.name, '考试')
        self.math_file.tags.add(tag)
        self.assertRedirects(
            self.client.post(reverse('library:tag_delete', args=[tag.pk])),
            reverse('library:tags'),
        )
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())
        self.assertTrue(File.objects.filter(pk=self.math_file.pk).exists())

    def test_admin_can_manage_tags(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('library:tag_create'), {'name': '高一'})

        self.assertRedirects(response, reverse('library:tags'))
        self.assertTrue(Tag.objects.filter(name='高一').exists())

    def test_search_files_are_paginated(self):
        for index in range(21):
            File.objects.create(
                name=f'复习资料{index:02d}.txt', folder=self.functions,
                storage_key=f'file-{index}.txt', size=1, mime_type='text/plain',
                uploader=self.teacher,
            )
        self.client.force_login(self.student)
        first = self.client.get(reverse('library:search'), {'q': '复习资料'})
        second = self.client.get(reverse('library:search'), {'q': '复习资料', 'page': 2})

        self.assertEqual(first.context['file_page'].paginator.count, 21)
        self.assertEqual(len(first.context['file_page']), 20)
        self.assertEqual(len(second.context['file_page']), 1)

    def test_invalid_filter_ids_return_404(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('library:search'), {'tag': 'abc'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('library:search'), {
            'subject': self.functions.pk,
        }).status_code, 404)
