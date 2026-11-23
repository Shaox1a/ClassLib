from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import PermissionGroup, User


def lock_groups():
    # All membership/permission mutations acquire the same ordered locks.
    list(PermissionGroup.objects.select_for_update().order_by('pk'))


def require_administrator():
    if not User.objects.filter(
        is_active=True, permission_group__can_manage_accounts=True,
        permission_group__can_manage_groups=True,
    ).exists():
        raise ValidationError('至少保留一个已启用且同时拥有账户管理、权限组管理权限的账户。')


@transaction.atomic
def save_profile(user_id, nickname, password=None, current_password=None):
    lock_groups()
    user = User.objects.select_for_update().get(pk=user_id)
    if not user.is_active:
        raise PermissionDenied
    fields = ['nickname']
    user.nickname = nickname
    if password:
        if not user.check_password(current_password or ''):
            raise ValidationError({'current_password': '当前密码不正确。'})
        user.set_password(password)
        fields.append('password')
    user.save(update_fields=fields)
    return user


@transaction.atomic
def save_account(user, password=None):
    lock_groups()
    if password:
        user.set_password(password)
    fields = ['nickname', 'permission_group', 'is_active']
    if password:
        fields.append('password')
    user.save(update_fields=fields if not user._state.adding else None)
    require_administrator()
    return user


@transaction.atomic
def bulk_accounts(users, action, group=None):
    lock_groups()
    selected = list(User.objects.select_for_update().filter(pk__in=[user.pk for user in users]))
    for user in selected:
        if action == 'reset':
            user.set_password(user.account_id)
            user.save(update_fields=['password'])
        elif action == 'move':
            user.permission_group = group
            user.save(update_fields=['permission_group'])
        else:
            raise ValidationError('无效的批量操作。')
    require_administrator()
    return len(selected)


@transaction.atomic
def save_group(group):
    lock_groups()
    group.save()
    require_administrator()
    return group


@transaction.atomic
def delete_group(group, replacement=None):
    lock_groups()
    if group.members.exists():
        if replacement is None or replacement.pk == group.pk:
            raise ValidationError('请选择其他权限组来接收组内账户。')
        group.members.update(permission_group=replacement)
    group.delete()
    require_administrator()
