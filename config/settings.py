"""Production settings for both the candidate deployment and the live domain."""
import os
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

REQUIRED_ENV = (
    'DJANGO_SECRET_KEY', 'DJANGO_ALLOWED_HOSTS', 'DATABASE_URL',
    'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY',
)
missing = [name for name in REQUIRED_ENV if not os.getenv(name, '').strip()]
if missing:
    raise ImproperlyConfigured('Missing production settings: ' + ', '.join(missing))

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
if SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured('Set a unique DJANGO_SECRET_KEY of at least 50 characters')
DEBUG = False


def env_list(name):
    return [value.strip() for value in os.getenv(name, '').split(',') if value.strip()]


ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must include a hostname')
if os.getenv('VERCEL') and os.getenv('VERCEL_URL'):
    ALLOWED_HOSTS.append(os.environ['VERCEL_URL'])

database_url = urlparse(os.environ['DATABASE_URL'])
if database_url.scheme not in {'postgres', 'postgresql'}:
    raise ValueError('DATABASE_URL must be a PostgreSQL URL')
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': unquote(database_url.path.lstrip('/')),
    'USER': unquote(database_url.username or ''),
    'PASSWORD': unquote(database_url.password or ''),
    'HOST': database_url.hostname,
    'PORT': database_url.port or 5432,
    'OPTIONS': {'sslmode': 'require', 'options': '-c search_path=classlib,public',
                'prepare_threshold': None},
    'CONN_MAX_AGE': 0,
    'DISABLE_SERVER_SIDE_CURSORS': True,
}}

SUPABASE_URL = os.environ['SUPABASE_URL'].strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY'].strip()
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET', '').strip() or 'classlib-private'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')
