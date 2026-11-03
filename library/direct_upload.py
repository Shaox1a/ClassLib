"""Browser uploads bypass the hosting payload limit; Django still validates bytes."""
import logging
from pathlib import PurePosixPath
from uuid import uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import storage
from .forms import ALLOWED_EXTENSIONS, UploadForm, clean_display_name
from .models import File, Folder
from .permissions import library_permission_required
from .services import create_file

logger = logging.getLogger(__name__)
SALT = 'classlib.direct-upload'


def completed(document):
    return JsonResponse({'redirect': reverse('library:file', args=[document.pk])})


@library_permission_required('upload')
@require_POST
def begin(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    if not settings.SUPABASE_URL:
        return JsonResponse({'error': '未配置云存储。'}, status=400)
    try:
        name = clean_display_name(request.POST.get('name', ''))
        size = int(request.POST.get('size', '0'))
        extension = PurePosixPath(name).suffix.lower()
        if len(name) > 255 or extension not in ALLOWED_EXTENSIONS:
            raise ValueError('文件名过长或文件类型不受支持。')
        if not 0 < size <= settings.MAX_UPLOAD_SIZE:
            raise ValueError('文件大小必须在 1 字节到 50 MiB 之间。')
        if File.objects.filter(folder=folder, name=name).exists():
            raise ValueError('这个文件夹已有同名文件。')
    except (ValueError, ValidationError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    key = uuid4().hex + extension
    ticket = signing.dumps({'user': request.user.pk, 'folder': folder.pk,
                            'key': key, 'name': name, 'size': size}, salt=SALT)
    try:
        url = storage.signed_upload('pending/' + key)
    except OSError:
        return JsonResponse({'error': '暂时无法连接存储，请稍后重试。'}, status=503)
    response = JsonResponse({'url': url, 'ticket': ticket})
    response['Cache-Control'] = 'private, no-store'
    return response


@library_permission_required('upload')
@require_POST
def finish(request, folder_id):
    get_object_or_404(Folder, pk=folder_id)
    try:
        payload = signing.loads(request.POST.get('ticket', ''), salt=SALT, max_age=7200)
        if payload['user'] != request.user.pk or payload['folder'] != folder_id:
            raise signing.BadSignature('Wrong upload owner')
    except signing.BadSignature:
        return JsonResponse({'error': '上传凭据无效或已过期，请重新选择文件。'}, status=400)
    key = payload['key']
    existing = File.objects.filter(storage_key=key, uploader=request.user).first()
    if existing:
        return completed(existing)
    pending_key = 'pending/' + key
    try:
        with storage.open_file(pending_key) as stream:
            content = stream.read()
        if len(content) != payload['size']:
            raise ValueError('上传文件大小与声明不符。')
        uploaded = SimpleUploadedFile(payload['name'], content)
        # Serialize finalization within this folder, including retries.
        with transaction.atomic():
            folder = get_object_or_404(Folder.objects.select_for_update(), pk=folder_id)
            existing = File.objects.filter(storage_key=key, uploader=request.user).first()
            if existing:
                return completed(existing)
            form = UploadForm({}, {'upload': uploaded}, folder=folder)
            if not form.is_valid():
                raise ValueError(' '.join(str(error) for errors in form.errors.values() for error in errors))
            document = create_file(folder=folder, uploaded_file=uploaded,
                                   name=form.file_name, uploader=request.user, storage_key=key)
    except ValueError as exc:
        storage.delete(pending_key)
        return JsonResponse({'error': str(exc)}, status=400)
    except OSError:
        return JsonResponse({'error': '存储服务暂时不可用，请重试。'}, status=503)
    # Only validated bytes are copied to the final key; upload links cannot overwrite it.
    try:
        storage.delete(pending_key)
    except OSError:
        logger.warning('Failed to clean temporary upload %s', pending_key)
    return completed(document)
