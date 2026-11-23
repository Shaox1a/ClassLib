"""Read the original SQLite database for the one-time data export."""
from config.base import *  # noqa: F403

SECRET_KEY = 'offline-export-only'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
SUPABASE_URL = ''
SUPABASE_SERVICE_ROLE_KEY = ''
SUPABASE_BUCKET = ''
