from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AccountCreationForm
from .models import User


def administrator_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN and not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


@administrator_required
def account_list(request):
    users = User.objects.order_by('username')
    return render(request, 'accounts/list.html', {'users': users})


@administrator_required
def account_create(request):
    form = AccountCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'账号 {user.username} 已创建。')
        return redirect('accounts:list')
    return render(request, 'accounts/create.html', {'form': form})


@administrator_required
@require_POST
def account_status(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if user.pk == request.user.pk or user.role == User.Role.ADMIN or user.is_superuser:
        raise PermissionDenied

    action = request.POST.get('action')
    if action not in {'activate', 'deactivate'}:
        raise PermissionDenied
    user.is_active = action == 'activate'
    user.save(update_fields=['is_active'])
    messages.success(request, f'账号 {user.username} 已{"启用" if user.is_active else "停用"}。')
    return redirect('accounts:list')
