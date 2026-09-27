from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from accounts.models import User


ROLE_PERMISSIONS = {
    User.Role.STUDENT: frozenset({'view', 'download'}),
    User.Role.TEACHER: frozenset({'view', 'download', 'upload', 'manage'}),
    User.Role.ADMIN: frozenset({'view', 'download', 'upload', 'manage'}),
}
LIBRARY_ACTIONS = frozenset({'view', 'download', 'upload', 'manage'})


def has_permission(user, action):
    if action not in LIBRARY_ACTIONS:
        raise ValueError(f'Unknown library action: {action}')
    return bool(
        user.is_authenticated and user.is_active
        and (user.is_superuser or action in ROLE_PERMISSIONS.get(user.role, ()))
    )


def library_permission_required(action):
    if action not in LIBRARY_ACTIONS:
        raise ValueError(f'Unknown library action: {action}')

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not has_permission(request.user, action):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
