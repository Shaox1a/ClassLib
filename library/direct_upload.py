"""Authorize private uploads without reading whole objects into Django."""
import logging
from uuid import uuid4
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from . import kodo, storage
from .forms import clean_display_name
from .models import File, Folder
from .permissions import library_permission_required
from .services import mime_type_for

logger = logging.getLogger(__name__)
SALT = 'classlib.direct-upload'

def completed(document):
    return JsonResponse({'redirect': reverse('library:file', args=[document.pk])})

def payload_for(request, folder_id):
    payload = signing.loads(request.POST.get('ticket', ''), salt=SALT, max_age=86400)
    if payload['user'] != request.user.pk or payload['folder'] != folder_id:
        raise signing.BadSignature('Wrong upload owner')
    return payload

@library_permission_required('upload')
@require_POST
def begin(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    if not (settings.KODO_BUCKET or settings.SUPABASE_URL):
        return JsonResponse({'error': '未配置云存储。'}, status=400)
    try:
        if request.POST.get('ticket'):
            payload = payload_for(request, folder_id)
        else:
            name = clean_display_name(request.POST.get('name', ''))
            size = int(request.POST.get('size', '-1'))
            if len(name) > 255 or size < 0:
                raise ValueError('Invalid name or size')
            if File.objects.filter(folder=folder, name=name).exists():
                raise ValueError('Duplicate name')
            payload = {'user': request.user.pk, 'folder': folder.pk, 'key': uuid4().hex,
                       'name': name, 'size': size}
            if settings.KODO_BUCKET:
                payload['upload_id'] = kodo.start(payload)
        ticket = request.POST.get('ticket') or signing.dumps(payload, salt=SALT)
        if settings.KODO_BUCKET:
            if 'upload_id' not in payload:
                raise ValueError('Storage provider changed')
            data = {'provider': 'kodo', 'ticket': ticket, 'partSize': kodo.part_size(payload['size'])}
            if 'part' in request.POST:
                data['url'] = kodo.part_url(payload, int(request.POST['part']))
            response = JsonResponse(data)
            response['Cache-Control'] = 'private, no-store'
            return response
        url = storage.signed_upload('pending/' + payload['key'])
    except (ValueError, ValidationError, signing.BadSignature):
        return JsonResponse({'error': '文件名、大小或上传凭据无效，或已存在同名文件。'}, status=400)
    except (OSError, BotoCoreError, ClientError):
        return JsonResponse({'error': '存储服务不可用，请稍后重试。'}, status=503)
    endpoint = settings.SUPABASE_URL.rstrip('/')
    if endpoint.endswith('.supabase.co'):
        endpoint = endpoint[:-len('.supabase.co')] + '.storage.supabase.co'
    response = JsonResponse({'url': url, 'ticket': ticket, 'key': 'pending/' + payload['key'],
                             'bucket': settings.SUPABASE_BUCKET,
                             'endpoint': endpoint + '/storage/v1/upload/resumable/sign'})
    response['Cache-Control'] = 'private, no-store'
    return response

@library_permission_required('upload')
@require_POST
def finish(request, folder_id):
    get_object_or_404(Folder, pk=folder_id)
    try:
        payload = payload_for(request, folder_id)
    except signing.BadSignature:
        return JsonResponse({'error': '上传凭据无效或已过期，请重新选择文件。'}, status=400)
    key = payload['key']
    pending = 'pending/' + key
    try:
        with transaction.atomic():
            folder = get_object_or_404(Folder.objects.select_for_update(), pk=folder_id)
            existing = File.objects.filter(storage_key=key, uploader=request.user).first()
            if existing:
                return completed(existing)
            if File.objects.filter(folder=folder, name=payload['name']).exists():
                return JsonResponse({'error': '这个文件夹已有同名文件。'}, status=400)
            if settings.KODO_BUCKET:
                if 'upload_id' not in payload:
                    raise ValueError('Storage provider changed')
                kodo.finish(payload)
            else:
                if storage.object_size(pending) != payload['size']:
                    return JsonResponse({'error': '上传大小与声明不符。'}, status=400)
                try:
                    storage.copy_object(pending, key)
                except OSError:
                    if storage.object_size(key) != payload['size']:
                        raise
            document = File.objects.create(folder=folder, name=payload['name'], storage_key=key,
                                           size=payload['size'], mime_type=mime_type_for(payload['name']),
                                           uploader=request.user)
    except IntegrityError:
        return JsonResponse({'error': '文件名冲突，请刷新后重试。'}, status=409)
    except ValueError:
        return JsonResponse({'error': '分片不完整或上传凭据无效。'}, status=400)
    except (OSError, BotoCoreError, ClientError):
        return JsonResponse({'error': '存储服务不可用，或平台大小/容量限制导致上传失败，请重试确认。'}, status=503)
    if settings.KODO_BUCKET:
        return completed(document)
    try:
        storage.delete(pending)
    except OSError:
        logger.warning('Failed to clean temporary upload %s', pending)
    return completed(document)
