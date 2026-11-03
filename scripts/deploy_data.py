"""Explicit one-time deployment helper. Credentials and exports stay local."""
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        os.environ[key.strip()] = value.strip().strip('\"\'')
mode = sys.argv[1]
if mode == 'export':
    os.environ.pop('DATABASE_URL', None)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.core.management import call_command
from django.core.files.base import ContentFile
from django.db import connection
from accounts.models import User
from library.models import File, Folder, Tag
from library import storage

if mode == 'verify':
    with connection.cursor() as cursor:
        cursor.execute('select current_database(), current_user')
        print('Postgres connection: OK')
    key = 'deployment-check-' + uuid4().hex + '.txt'
    content = b'ClassLib private storage connection check'
    storage.save(key, ContentFile(content))
    try:
        with storage.open_file(key) as remote:
            assert remote.read() == content
        print('Private storage write/read: OK')
    finally:
        storage.delete(key)
    print('Private storage delete: OK')
elif mode == 'export':
    directory = ROOT / 'deploy-private'
    directory.mkdir(exist_ok=True)
    exported = StringIO()
    call_command('dumpdata', natural_foreign=True, natural_primary=True,
                 exclude=['contenttypes', 'auth.permission', 'sessions', 'admin.logentry'],
                 stdout=exported)
    (directory / 'data.json').write_text(exported.getvalue(), encoding='utf-8')
    print(json.dumps({'users': User.objects.count(), 'folders': Folder.objects.count(),
                      'files': File.objects.count(), 'tags': Tag.objects.count()}))
elif mode == 'migrate':
    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS classlib')
        cursor.execute('REVOKE ALL ON SCHEMA classlib FROM PUBLIC, anon, authenticated')
    call_command('migrate', interactive=False)
    if User.objects.exists() or Folder.objects.exists() or File.objects.exists():
        raise RuntimeError('Target already contains application data; inspect before importing')
    call_command('loaddata', str(ROOT / 'deploy-private' / 'data.json'))
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'classlib'")
        tables = [row[0] for row in cursor.fetchall()]
        from psycopg import sql
        for table in tables:
            cursor.execute(sql.SQL('ALTER TABLE classlib.{} ENABLE ROW LEVEL SECURITY').format(sql.Identifier(table)))
    print('Application data migrated; private schema and RLS enabled')
elif mode == 'files':
    for document in File.objects.all():
        path = (ROOT / 'private_files' / document.storage_key).resolve()
        if (ROOT / 'private_files').resolve() not in path.parents:
            raise RuntimeError('Unsafe storage key')
        content = path.read_bytes()
        assert len(content) == document.size
        # Fresh cloud project: fail rather than overwrite an unexpected existing object.
        storage.save(document.storage_key, ContentFile(content))
        with storage.open_file(document.storage_key) as remote:
            assert hashlib.sha256(remote.read()).digest() == hashlib.sha256(content).digest()
    print(f'Uploaded and SHA-256 verified {File.objects.count()} objects')
elif mode == 'audit':
    print(json.dumps({'users': User.objects.count(), 'folders': Folder.objects.count(),
                      'files': File.objects.count(), 'tags': Tag.objects.count()}))
