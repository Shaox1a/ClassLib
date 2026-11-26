import mimetypes
from pathlib import PurePosixPath
from uuid import uuid4

from django.db import transaction
from django.db.models import Max

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


def next_folder_position(parent):
    current = Folder.objects.filter(parent=parent).aggregate(high=Max('position'))['high']
    return 0 if current is None else current + 1


def place_folder_at_end(folder):
    folder.position = next_folder_position(folder.parent_id)
    folder.save(update_fields=['position'])


def set_folder_positions(parent, ordered_ids):
    siblings = list(Folder.objects.filter(parent=parent).order_by('position', 'pk'))
    if len(ordered_ids) != len(siblings):
        return False
    if set(ordered_ids) != {folder.pk for folder in siblings}:
        return False
    with transaction.atomic():
        for position, folder_id in enumerate(ordered_ids):
            Folder.objects.filter(pk=folder_id, parent=parent).update(position=position)
    return True


def reorder_folder(folder, direction):
    if direction not in {'up', 'down'}:
        return False
    with transaction.atomic():
        siblings = list(
            Folder.objects.select_for_update()
            .filter(parent=folder.parent)
            .order_by('position', 'pk'),
        )
        index = next((i for i, item in enumerate(siblings) if item.pk == folder.pk), None)
        if index is None:
            return False
        offset = -1 if direction == 'up' else 1
        target = index + offset
        if target < 0 or target >= len(siblings):
            return False
        partner = siblings[target]
        partner_pos, folder_pos = partner.position, folder.position
        Folder.objects.filter(pk=partner.pk).update(position=folder_pos)
        Folder.objects.filter(pk=folder.pk).update(position=partner_pos)
        return True


def delete_folder(folder):
    with transaction.atomic():
        folder_ids = descendant_folder_ids(folder)
        keys = list(File.objects.filter(folder_id__in=folder_ids).values_list('storage_key', flat=True))
        folder.delete()

        def cleanup_deleted_files():
            for key in keys:
                delete_object(key)

        transaction.on_commit(cleanup_deleted_files)
