"""Local development: SQLite and on-disk private_files (no Supabase)."""
from .base import *  # noqa: F403

SECRET_KEY = 'django-insecure-local-dev-only-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

SUPABASE_URL = ''
SUPABASE_SERVICE_ROLE_KEY = ''
SUPABASE_BUCKET = 'classlib-private'