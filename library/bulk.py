from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import File, Folder
from .permissions import library_permission_required
from .services import delete_file, delete_folder, folder_tree_ids


def selected_children(queryset, raw_ids):
    tokens = raw_ids.split(',') if raw_ids else []
    if any(not token.isascii() or not token.isdigit() or len(token) > 19 for token in tokens):
        raise ValidationError('选择无效，请返回文件夹重新选择。')
    ids = {int(token) for token in tokens}
    items = list(queryset.select_for_update().filter(pk__in=ids))
    if len(items) != len(ids):
        raise ValidationError('部分所选项目已不在当前文件夹，请重新选择。')
    return items


def move_items(folders, files, destination):
    folder_ids = [item.pk for item in folders]
    file_ids = [item.pk for item in files]
    if Folder.objects.filter(parent=destination, name__in=[item.name for item in folders]).exists():
        raise ValidationError('目标位置已有同名文件夹，请选择其他位置。')
    if File.objects.filter(folder=destination, name__in=[item.name for item in files]).exists():
        raise ValidationError('目标位置已有同名文件，请选择其他位置。')
    now = timezone.now()
    Folder.objects.filter(pk__in=folder_ids).update(parent=destination, updated_at=now)
    File.objects.filter(pk__in=file_ids).update(folder=destination, updated_at=now)


@library_permission_required('manage')
@require_POST
def folder_bulk(request, folder_id):
    action = request.POST.get('action')
    source = get_object_or_404(Folder, pk=folder_id)
    context = {'source': source, 'action': action}
    try:
        with transaction.atomic():
            folders = selected_children(source.children, request.POST.get('folders', ''))
            files = selected_children(source.files, request.POST.get('files', ''))
            if action not in ('move', 'delete') or not (folders or files):
                raise ValidationError('请选择要移动或删除的项目。')
            context.update(folders=folders, files=files, count=len(folders) + len(files),
                           folder_ids=','.join(str(item.pk) for item in folders),
                           file_ids=','.join(str(item.pk) for item in files))
            if action == 'move':
                excluded = folder_tree_ids([item.pk for item in folders]) | {source.pk}
                destinations = Folder.objects.exclude(pk__in=excluded)
                context['destinations'] = destinations.select_related('parent')
            if request.POST.get('confirm') != '1':
                return render(request, 'library/bulk.html', context)
            if action == 'move':
                target = request.POST.get('destination', '')
                if target == 'root' and not files:
                    destination = None
                else:
                    if not target.isascii() or not target.isdigit() or len(target) > 19:
                        raise ValidationError('请选择目标文件夹。')
                    destination = destinations.select_for_update().filter(pk=int(target)).first()
                    if destination is None:
                        raise ValidationError('该位置不能作为移动目标，请重新选择。')
                move_items(folders, files, destination)
            else:
                for folder in folders:
                    delete_folder(folder)
                for document in files:
                    delete_file(document)
    except ValidationError as error:
        context['error'] = error.messages[0]
        return render(request, 'library/bulk.html', context, status=400)
    except IntegrityError:
        context['error'] = '目标位置或所选项目已发生变化，请重新检查。'
        return render(request, 'library/bulk.html', context, status=409)
    verb = '移动' if action == 'move' else '删除'
    messages.success(request, f'已{verb} {len(folders) + len(files)} 项。')
    return redirect('library:folder', folder_id=source.pk)
