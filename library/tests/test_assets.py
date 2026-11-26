import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.template import Context, Template
from django.test import SimpleTestCase

from library.templatetags.assets import asset


class AssetVersionTests(SimpleTestCase):
    def test_url_changes_with_content_without_restarting_the_process(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'site.css'
            path.write_bytes(b'.old { display: block; }')
            with patch('library.templatetags.assets.finders.find', return_value=str(path)):
                first = asset('css/site.css')
                self.assertEqual(first, asset('css/site.css'))
                path.write_bytes(b'.new { display: grid; }')
                second = asset('css/site.css')
                self.assertNotEqual(first, second)
                self.assertTrue(second.endswith(hashlib.sha256(path.read_bytes()).hexdigest()[:16]))

    def test_base_and_view_control_templates_use_versioned_assets(self):
        page = Template("{% extends 'base.html' %}{% block content %}{% include 'library/view_toggle.html' %}{% endblock %}")
        html = page.render(Context({}))
        self.assertIn('/static/css/site.css?v=', html)
        self.assertIn('/static/js/view.js?v=', html)
