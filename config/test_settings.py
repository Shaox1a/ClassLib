"""Isolated settings for Django unit tests and migration consistency checks."""
from .base import *  # noqa: F403

SECRET_KEY = 'unit-test-only'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SUPABASE_URL = ''
SUPABASE_SERVICE_ROLE_KEY = ''
SUPABASE_BUCKET = 'classlib-private'
