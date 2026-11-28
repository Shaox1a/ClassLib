from django.test import SimpleTestCase, override_settings

from .storage import _request


@override_settings(SUPABASE_URL='https://example.supabase.co', SUPABASE_BUCKET='private')
class StorageAuthenticationTests(SimpleTestCase):
    @override_settings(SUPABASE_SERVICE_ROLE_KEY='sb_secret_test')
    def test_modern_secret_is_only_an_api_key(self):
        request = _request('file.txt', 'GET')
        self.assertEqual(request.get_header('Apikey'), 'sb_secret_test')
        self.assertIsNone(request.get_header('Authorization'))

    @override_settings(SUPABASE_SERVICE_ROLE_KEY='legacy-jwt')
    def test_legacy_key_is_also_a_bearer_token(self):
        request = _request('file.txt', 'GET')
        self.assertEqual(request.get_header('Authorization'), 'Bearer legacy-jwt')
