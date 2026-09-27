from django.db.models import Q

from .models import File, Folder
from .services import folder_tree_ids


def search_library(*, query, subject=None, tag=None):
    """Search file names, folder names and tags; root folders act as subjects."""
    files = File.objects.select_related('folder', 'uploader').prefetch_related('tags')
    folders = Folder.objects.none()

    if query:
        folders = Folder.objects.filter(name__icontains=query)
        matching_folder_ids = folder_tree_ids(folders.values_list('pk', flat=True))
        files = files.filter(
            Q(name__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(folder_id__in=matching_folder_ids)
        )
    elif subject is not None:
        folders = Folder.objects.filter(pk__in=folder_tree_ids([subject.pk]))

    if subject is not None:
        subject_folder_ids = folder_tree_ids([subject.pk])
        files = files.filter(folder_id__in=subject_folder_ids)
        folders = folders.filter(pk__in=subject_folder_ids)

    if tag is not None:
        files = files.filter(tags=tag)
        folders = Folder.objects.none()

    return folders.order_by('name', 'pk'), files.distinct().order_by('-created_at', '-pk')
