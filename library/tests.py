from django.test import TestCase
from django.urls import reverse


class LibraryPageTests(TestCase):
    def test_home_page_lists_phase_one_folders(self):
        response = self.client.get(reverse('library:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '数学')
        self.assertContains(response, '搜索文件或文件夹')

    def test_folder_page_renders_known_folder(self):
        response = self.client.get(reverse('library:folder', args=[1]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '语文')

    def test_unknown_folder_returns_404(self):
        response = self.client.get(reverse('library:folder', args=[999]))

        self.assertEqual(response.status_code, 404)

    def test_search_keeps_query_in_response(self):
        response = self.client.get(reverse('library:search'), {'q': '函数'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '函数')
