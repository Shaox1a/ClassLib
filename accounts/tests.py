from django.test import TestCase
from django.urls import reverse


class AuthenticationPageTests(TestCase):
    def test_login_page_is_available(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '登录 ClassLib')

    def test_login_redirects_to_home(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user(username='student', password='safe-password')
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'student', 'password': 'safe-password'},
        )

        self.assertRedirects(response, reverse('library:home'))
