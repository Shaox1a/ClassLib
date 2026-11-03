"""Private object storage, separate from metadata and permissions."""

from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def _local():
    return FileSystemStorage(location=settings.PRIVATE_FILE_ROOT)


def _request(key, method, data=None):
    url = (f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
           f"{settings.SUPABASE_BUCKET}/{quote(key, safe='')}")
    headers = {
        'Authorization': f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}',
        'apikey': settings.SUPABASE_SERVICE_ROLE_KEY,
    }
    if data is not None:
        headers['Content-Type'] = 'application/octet-stream'
    return Request(url, data=data, headers=headers, method=method)


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
            return BytesIO(response.read())
    except HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(key) from exc
        raise
