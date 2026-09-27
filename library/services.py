import mimetypes
from pathlib import PurePosixPath
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction

from .models import File, Folder


def private_storage():
    return FileSystemStorage(location=settings.PRIVATE_FILE_ROOT)


def save_upload(uploaded_file, extension):
    key = f'{uuid4().hex}{extension}'
    uploaded_file.seek(0)
    return private_storage().save(key, uploaded_file)


def delete_object(storage_key):
    private_storage().delete(storage_key)


def open_download(storage_key):
    return private_storage().open(storage_key, 'rb')


def mime_type_for(name):
    return mimetypes.guess_type(name)[0] or 'application/octet-stream'


def create_file(*, folder, uploaded_file, name, uploader):
    extension = PurePosixPath(name).suffix.lower()
    key = save_upload(uploaded_file, extension)
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
