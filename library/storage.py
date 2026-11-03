"""Private object storage, separate from metadata and permissions."""

from io import BytesIO
import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _local():
    return FileSystemStorage(location=settings.PRIVATE_FILE_ROOT)


def _request(key, method, data=None, operation=''):
    url = (f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
           f"{operation}{settings.SUPABASE_BUCKET}/{quote(key, safe='/')}")
    key_value = settings.SUPABASE_SERVICE_ROLE_KEY
    headers = {'apikey': key_value}
    # Modern secret keys are opaque API keys, not JWT bearer tokens.
    if not key_value.startswith('sb_secret_'):
        headers['Authorization'] = f'Bearer {key_value}'
    if data is not None:
        headers['Content-Type'] = 'application/octet-stream'
    return Request(url, data=data, headers=headers, method=method)


def _sign(key, operation, payload, response_key):
    request = _request(key, 'POST', json.dumps(payload).encode(), operation=operation)
    request.add_header('Content-Type', 'application/json')
    with urlopen(request, timeout=30) as response:
        path = json.load(response)[response_key]
    return settings.SUPABASE_URL.rstrip('/') + '/storage/v1' + path


def signed_upload(key):
    return _sign(key, 'upload/sign/', {}, 'url')


def signed_download(key, filename):
    url = _sign(key, 'sign/', {'expiresIn': 60}, 'signedURL')
    return url + '&download=' + quote(filename, safe='')


def save(key, uploaded_file):
    uploaded_file.seek(0)
    if not settings.SUPABASE_URL:
        return _local().save(key, uploaded_file)
    with urlopen(_request(key, 'POST', uploaded_file.read()), timeout=120):
        return key


def delete(key):
    if not settings.SUPABASE_URL:
        return _local().delete(key)
    try:
        with urlopen(_request(key, 'DELETE'), timeout=30):
            pass
    except HTTPError as exc:
        if exc.code != 404:
            raise


def open_file(key):
    if not settings.SUPABASE_URL:
        return _local().open(key, 'rb')
    try:
        with urlopen(_request(key, 'GET'), timeout=120) as response:
            data = response.read(settings.MAX_UPLOAD_SIZE + 1)
            if len(data) > settings.MAX_UPLOAD_SIZE:
                raise ValueError('文件不能超过 50 MiB。')
            return BytesIO(data)
    except HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(key) from exc
        raise
