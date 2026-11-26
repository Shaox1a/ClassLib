import mimetypes
from pathlib import PurePosixPath
from uuid import uuid4

from django.db import transaction

from .models import File, Folder
from . import storage


def save_upload(uploaded_file, extension):
    key = f'{uuid4().hex}{extension}'
    return storage.save(key, uploaded_file)


def delete_object(storage_key):
    storage.delete(storage_key)


def open_download(storage_key):
    return storage.open_file(storage_key)


def mime_type_for(name):
    return mimetypes.guess_type(name)[0] or 'application/octet-stream'


def preview_kind(name, mime_type=''):
    mime = mime_type or mime_type_for(name)
    lower = name.lower()
    if mime.startswith('image/'):
        return 'image'
    if mime == 'application/pdf' or lower.endswith('.pdf'):
        return 'pdf'
    if mime.startswith('text/') or mime in {'application/json', 'application/xml'}:
        return 'text'
    if lower.endswith(('.txt', '.md', '.csv', '.log', '.json', '.xml', '.html', '.htm', '.css', '.js')):
        return 'text'
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('audio/'):
        return 'audio'
    return 'none'


def create_file(*, folder, uploaded_file, name, uploader, storage_key=None):
    extension = PurePosixPath(name).suffix.lower()
    key = storage.save(storage_key, uploaded_file) if storage_key else save_upload(uploaded_file, extension)
    try:
        return File.objects.create(
            name=name,
            folder=folder,
            storage_key=key,
            size=uploaded_file.size,
            mime_type=mime_type_for(name),
            uploader=uploader,
        )
    except Exception:
        delete_object(key)
        raise


def descendant_folder_ids(folder):
    return folder_tree_ids([folder.pk])


def folder_tree_ids(root_ids):
    result = set()
    pending = set(root_ids)
    while pending:
        fresh = pending - result
        if not fresh:
            break
        result.update(fresh)
        pending = set(Folder.objects.filter(parent_id__in=fresh).values_list('pk', flat=True))
    return result


def delete_file(file):
    key = file.storage_key
    with transaction.atomic():
        file.delete()
        transaction.on_commit(lambda: delete_object(key))


def delete_folder(folder):
    with transaction.atomic():
        folder_ids = descendant_folder_ids(folder)
        keys = list(File.objects.filter(folder_id__in=folder_ids).values_list('storage_key', flat=True))
        folder.delete()

        def cleanup_deleted_files():
            for key in keys:
                delete_object(key)

        transaction.on_commit(cleanup_deleted_files)
