"""Exercise production HTTP routes with temporary users and remove test data."""
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPCookieProcessor, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        os.environ[key.strip()] = value.strip().strip('\"\'')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from accounts.models import User
from django.contrib.sessions.models import Session
from library.models import Folder, File
from library.services import delete_folder

BASE = 'https://classlib-theta.vercel.app'
sessions = []
users = []
folder = None
checks = []


def client():
    jar = CookieJar()
    sessions.append(jar)
    return build_opener(HTTPCookieProcessor(jar)), jar


def get(opener, path):
    return opener.open(BASE + path, timeout=90)


def post(opener, jar, path, values):
    csrf = next(c.value for c in jar if c.name == 'csrftoken')
    request = Request(BASE + path, data=urlencode(values).encode(), headers={
        'X-CSRFToken': csrf, 'Referer': BASE + path, 'Origin': BASE,
    })
    return opener.open(request, timeout=180)


def login(role):
    password = secrets.token_urlsafe(32)
    user = User.objects.create_user(username='deployment_' + uuid4().hex, password=password, role=role)
    users.append(user)
    opener, jar = client()
    with get(opener, '/login/') as response:
        assert b'csrfmiddlewaretoken' in response.read()
    with post(opener, jar, '/login/', {'username': user.username, 'password': password}) as response:
        assert urlparse(response.url).path == '/', 'Login did not redirect to library'
    assert any(c.name == 'sessionid' and c.secure for c in jar)
    return opener, jar


try:
    anonymous, _ = client()
    with get(anonymous, '/') as response:
        assert urlparse(response.url).path == '/login/'
    checks.append('Anonymous users must log in')
    teacher, teacher_jar = login(User.Role.TEACHER)
    checks.append('Teacher login and secure session cookie')
    name = 'deployment-check-' + uuid4().hex
    with post(teacher, teacher_jar, '/folder/new/', {'name': name}) as response:
        assert response.status == 200
    folder = Folder.objects.get(name=name)
    upload_path = f'/folder/{folder.pk}/upload/'
    with get(teacher, upload_path) as response:
        assert b'data-direct-upload' in response.read()
    for asset in ['/static/css/site.css', '/static/js/upload.js']:
        with get(teacher, asset) as response:
            assert response.status == 200 and response.read()
    checks.append('Upload form and static assets')
    content = b'ClassLib production check\n' * 220000
    assert len(content) > 5 * 1024 * 1024
    with post(teacher, teacher_jar, upload_path + 'begin/', {'name': 'check.txt', 'size': len(content)}) as response:
        upload = json.load(response)
    with urlopen(Request(upload['url'], method='OPTIONS', headers={
        'Origin': BASE, 'Access-Control-Request-Method': 'PUT',
        'Access-Control-Request-Headers': 'content-type',
    }), timeout=60) as response:
        assert response.headers.get('Access-Control-Allow-Origin') in ('*', BASE)
    with urlopen(Request(upload['url'], data=content, method='PUT', headers={
        'Content-Type': 'application/octet-stream', 'Origin': BASE,
    }), timeout=180) as response:
        assert response.status in (200, 201)
    with post(teacher, teacher_jar, upload_path + 'finish/', {'ticket': upload['ticket']}) as response:
        document_url = json.load(response)['redirect']
    document = File.objects.get(folder=folder, name='check.txt')
    assert document.size == len(content)
    with post(teacher, teacher_jar, upload_path + 'finish/', {'ticket': upload['ticket']}) as response:
        assert json.load(response)['redirect'] == document_url
    checks.append('Over-5-MiB direct upload, CORS, content validation, idempotent confirmation')
    student, student_jar = login(User.Role.STUDENT)
    try:
        post(student, student_jar, upload_path + 'begin/', {'name': 'blocked.txt', 'size': 5})
        raise AssertionError('Student was allowed to upload')
    except HTTPError as error:
        assert error.code == 403
    with get(student, f'/file/{document.pk}/download/') as response:
        assert urlparse(response.url).hostname == 'imrtztgljhjphbuajptk.supabase.co'
        assert hashlib.sha256(response.read()).digest() == hashlib.sha256(content).digest()
    checks.append('Student upload denied; authenticated signed download matches content')
    original = File.objects.exclude(folder=folder).first()
    with get(student, f'/file/{original.pk}/download/') as response:
        assert hashlib.sha256(response.read()).digest() == hashlib.sha256(
            (ROOT / 'private_files' / original.storage_key).read_bytes()).digest()
    checks.append('Migrated original file downloads with matching SHA-256')
    with post(teacher, teacher_jar, f'/file/{document.pk}/delete/', {}) as response:
        assert response.status == 200
    assert not File.objects.filter(pk=document.pk).exists()
    from library import storage
    try:
        storage.open_file(document.storage_key)
        raise AssertionError('Deleted object still readable')
    except (FileNotFoundError, HTTPError):
        pass
    checks.append('File deletion removes metadata and object')
finally:
    if folder and Folder.objects.filter(pk=folder.pk).exists():
        delete_folder(folder)
    for jar in sessions:
        for cookie in jar:
            if cookie.name == 'sessionid':
                Session.objects.filter(session_key=cookie.value).delete()
    for user in users:
        user.delete()

print(json.dumps({'passed': checks, 'cleanup': 'complete'}, ensure_ascii=True))
