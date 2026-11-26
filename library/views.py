from urllib.parse import urlencode
from uuid import UUID

from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .forms import (
    FileMoveForm, FileNameForm, FolderMoveForm, FolderNameForm,
    UploadForm,
)
from .models import File, Folder
from .permissions import has_permission, library_permission_required
from .search import search_library
from .services import create_file, delete_file, delete_folder, open_download, preview_kind
from . import storage
from .browsing import sort_options


def can_manage(user):
    return has_permission(user, 'manage')


def folder_breadcrumbs(folder):
    path = []
    while folder is not None:
        path.append(folder)
        folder = folder.parent
    return list(reversed(path))


def edit_page(request, *, title, form, back_url, submit_label='保存', is_upload=False):
    return render(request, 'library/form.html', {
        'title': title,
        'form': form,
        'back_url': back_url,
        'submit_label': submit_label,
        'is_upload': is_upload,
        'direct_upload': is_upload and bool(settings.SUPABASE_URL),
    })


@library_permission_required('view')
def home(request):
    ordering, sorting = sort_options(request)
    folders = Folder.objects.filter(parent__isnull=True).select_related('uploader').order_by(*ordering)
    return render(request, 'library/home.html', {
        'folders': folders,
        **sorting,
        'can_manage': can_manage(request.user),
    })


@library_permission_required('view')
def folder_detail(request, folder_id):
    ordering, sorting = sort_options(request)
    folder = get_object_or_404(Folder, pk=folder_id)
    return render(request, 'library/folder.html', {
        'folder': folder,
        'breadcrumbs': folder_breadcrumbs(folder),
        'subfolders': folder.children.select_related('uploader').order_by(*ordering),
        **sorting,
        'files': folder.files.select_related('uploader').order_by(*ordering),
        'can_manage': can_manage(request.user),
        'can_upload': has_permission(request.user, 'upload'),
    })


@library_permission_required('manage')
def folder_create(request, parent_id=None):
    parent = get_object_or_404(Folder, pk=parent_id) if parent_id is not None else None
    form = FolderNameForm(request.POST if request.method == 'POST' else None, parent=parent)
    if request.method == 'POST' and form.is_valid():
        folder = form.save(commit=False)
        folder.parent = parent
        folder.uploader = request.user
        folder.save()
        messages.success(request, '文件夹已创建。')
        return redirect('library:folder', folder_id=folder.pk)
    back_url = reverse('library:folder', args=[parent.pk]) if parent else reverse('library:home')
    return edit_page(request, title='创建文件夹', form=form, back_url=back_url, submit_label='创建')


@library_permission_required('manage')
def folder_rename(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    form = FolderNameForm(request.POST if request.method == 'POST' else None, instance=folder)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '文件夹已重命名。')
        return redirect('library:folder', folder_id=folder.pk)
    return edit_page(request, title='重命名文件夹', form=form,
                     back_url=reverse('library:folder', args=[folder.pk]))


@library_permission_required('manage')
def folder_move(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    form = FolderMoveForm(request.POST if request.method == 'POST' else None, instance=folder)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '文件夹已移动。')
        return redirect('library:folder', folder_id=folder.pk)
    return edit_page(request, title='移动文件夹', form=form,
                     back_url=reverse('library:folder', args=[folder.pk]))


@library_permission_required('manage')
def folder_delete(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    back_url = reverse('library:folder', args=[folder.pk])
    if request.method == 'POST':
        destination = reverse('library:folder', args=[folder.parent_id]) if folder.parent_id else reverse('library:home')
        delete_folder(folder)
        messages.success(request, '文件夹及其中的文件已删除。')
        return redirect(destination)
    return render(request, 'library/confirm_delete.html', {
        'title': '删除文件夹',
        'name': folder.name,
        'warning': '此操作会同时删除全部子文件夹和文件。',
        'back_url': back_url,
    })


@library_permission_required('upload')
def file_upload(request, folder_id):
    folder = get_object_or_404(Folder, pk=folder_id)
    upload_key = None
    if request.method == 'POST' and request.headers.get('X-Upload-Id'):
        try:
            upload_key = f'local-{request.user.pk}-' + UUID(request.headers['X-Upload-Id']).hex
        except ValueError:
            return JsonResponse({'error': '上传标识无效。'}, status=400)
        existing = File.objects.filter(storage_key=upload_key, uploader=request.user, folder=folder).first()
        if existing:
            return JsonResponse({'redirect': reverse('library:file', args=[existing.pk])})
    form = UploadForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        folder=folder,
    )
    if request.method == 'POST' and form.is_valid():
        document = create_file(
            folder=folder,
            uploaded_file=form.cleaned_data['upload'],
            name=form.file_name,
            uploader=request.user,
            storage_key=upload_key,
        )
        if request.headers.get('X-Upload-Queue') == '1':
            return JsonResponse({'redirect': reverse('library:file', args=[document.pk])})
        messages.success(request, '文件已上传。')
        return redirect('library:file', file_id=document.pk)
    if request.method == 'POST' and request.headers.get('X-Upload-Queue') == '1':
        return JsonResponse({'error': ' '.join(str(e) for errors in form.errors.values() for e in errors)}, status=400)
    return edit_page(request, title=f'上传到 {folder.name}', form=form,
                     back_url=reverse('library:folder', args=[folder.pk]),
                     submit_label='上传', is_upload=True)


@library_permission_required('view')
def file_detail(request, file_id):
    document = get_object_or_404(
        File.objects.select_related('folder', 'uploader'), pk=file_id
    )
    kind = preview_kind(document.name, document.mime_type)
    return render(request, 'library/file.html', {
        'document': document,
        'breadcrumbs': folder_breadcrumbs(document.folder),
        'preview_kind': kind,
        'can_manage': can_manage(request.user),
        'can_download': has_permission(request.user, 'download'),
    })


@library_permission_required('view')
@xframe_options_sameorigin
def file_preview(request, file_id):
    document = get_object_or_404(File, pk=file_id)
    try:
        stream = open_download(document.storage_key)
    except (FileNotFoundError, OSError) as exc:
        raise Http404('文件内容不存在。') from exc
    content_type = document.mime_type or 'application/octet-stream'
    if content_type == 'application/octet-stream' and document.name.lower().endswith('.pdf'):
        content_type = 'application/pdf'
    response = FileResponse(stream, as_attachment=False, filename=document.name)
    response['Content-Type'] = content_type
    response['Content-Disposition'] = content_disposition_header(False, document.name)
    response['Cache-Control'] = 'private, no-store'
    return response


@library_permission_required('download')
def file_download(request, file_id):
    document = get_object_or_404(File, pk=file_id)
    if settings.SUPABASE_URL:
        response = redirect(storage.signed_download(document.storage_key, document.name))
        response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response
    try:
        stream = open_download(document.storage_key)
    except (FileNotFoundError, OSError) as exc:
        raise Http404('文件内容不存在。') from exc
    response = FileResponse(stream, as_attachment=True, filename=document.name)
    response['Cache-Control'] = 'private, no-store'
    return response


@library_permission_required('manage')
def file_rename(request, file_id):
    document = get_object_or_404(File, pk=file_id)
    form = FileNameForm(request.POST if request.method == 'POST' else None, instance=document)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '文件已重命名。')
        return redirect('library:file', file_id=document.pk)
    return edit_page(request, title='重命名文件', form=form,
                     back_url=reverse('library:file', args=[document.pk]))


@library_permission_required('manage')
def file_move(request, file_id):
    document = get_object_or_404(File, pk=file_id)
    form = FileMoveForm(request.POST if request.method == 'POST' else None, instance=document)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '文件已移动。')
        return redirect('library:file', file_id=document.pk)
    return edit_page(request, title='移动文件', form=form,
                     back_url=reverse('library:file', args=[document.pk]))


@library_permission_required('manage')
def file_delete(request, file_id):
    document = get_object_or_404(File, pk=file_id)
    back_url = reverse('library:file', args=[document.pk])
    if request.method == 'POST':
        destination = reverse('library:folder', args=[document.folder_id])
        delete_file(document)
        messages.success(request, '文件已删除。')
        return redirect(destination)
    return render(request, 'library/confirm_delete.html', {
        'title': '删除文件',
        'name': document.name,
        'warning': '删除后无法在资料库中恢复。',
        'back_url': back_url,
    })


def selected_filter(model, raw_id, **filters):
    if not raw_id:
        return None
    try:
        pk = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise Http404('筛选条件不存在。') from exc
    return get_object_or_404(model, pk=pk, **filters)


@library_permission_required('view')
def search(request):
    ordering, sorting = sort_options(request)
    query = request.GET.get('q', '').strip()[:200]
    subject = selected_filter(Folder, request.GET.get('subject'), parent__isnull=True)
    has_searched = bool(query or subject)
    folders = Folder.objects.none()
    file_page = None
    if has_searched:
        folders, files = search_library(query=query, subject=subject)
        folders = folders.select_related('uploader').order_by(*ordering)
        files = files.order_by(*ordering)
        file_page = Paginator(files, 20).get_page(request.GET.get('page'))

    filter_query = urlencode({
        key: value for key, value in {
            'q': query,
            'subject': subject.pk if subject else '',
            'sort': sorting['sort_column'],
            'direction': sorting['sort_direction'],
        }.items() if value
    })
    return render(request, 'library/search.html', {
        **sorting,
        'query': query,
        'subjects': Folder.objects.filter(parent__isnull=True),
        'selected_subject': subject,
        'has_searched': has_searched,
        'folders': folders,
        'file_page': file_page,
        'filter_query': filter_query,
    })
