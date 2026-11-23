from functools import wraps

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .forms import (AccountCreationForm, AccountEditForm, BulkAccountForm, GroupDeleteForm,
                    LoginForm, PermissionGroupForm, ProfileForm)
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import JsonResponse
from .models import PermissionGroup, User
from . import services


class LoginView(DjangoLoginView):
    authentication_form = LoginForm

    def get_default_redirect_url(self):
        if not self.request.user.permission_group.can_view:
            return reverse('accounts:profile')
        return super().get_default_redirect_url()

    def form_invalid(self, form):
        if self.request.headers.get('X-Login-Form') == '1':
            return JsonResponse({'error': 'ID、昵称或密码不正确，请重试。'}, status=400)
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Login-Form') == '1':
            return JsonResponse({'redirect': self.get_success_url()})
        return response


def group_permission_required(permission):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not getattr(request.user.permission_group, permission):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


administrator_required = group_permission_required('can_manage_accounts')
groups_required = group_permission_required('can_manage_groups')


def form_page(request, form, title, back='accounts:list', account=None, note=''):
    return render(request, 'accounts/form.html', {
        'form': form, 'title': title, 'back': back, 'account': account, 'note': note,
    })


def management_redirect(request, destination):
    user = User.objects.select_related('permission_group').get(pk=request.user.pk)
    permission = 'can_manage_groups' if destination == 'accounts:groups' else 'can_manage_accounts'
    return redirect(destination if user.is_active and getattr(user.permission_group, permission) else 'accounts:profile')


@login_required
def profile(request):
    form = ProfileForm(request.POST if request.method == 'POST' else None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            user = services.save_profile(request.user.pk, form.cleaned_data['nickname'],
                                         form.cleaned_data.get('new_password1'), form.cleaned_data.get('current_password'))
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, '昵称已被使用，请刷新后重试。')
        else:
            if form.cleaned_data.get('new_password1'):
                update_session_auth_hash(request, user)
            messages.success(request, '账户信息已更新。')
            return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form})


@administrator_required
def account_list(request):
    return render(request, 'accounts/list.html', {
        'users': User.objects.select_related('permission_group').order_by('username'),
        'bulk_form': BulkAccountForm(),
    })


@administrator_required
def account_create(request):
    form = AccountCreationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        try:
            services.save_account(user, form.cleaned_data.get('new_password1') or user.account_id)
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, 'ID 或昵称已被使用，请刷新后重试。')
        else:
            messages.success(request, f'账户 {user.account_id} 已创建。')
            return redirect('accounts:list')
    return form_page(request, form, '创建账户', note='新密码留空时，默认密码为账户 ID。')


@administrator_required
def account_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = AccountEditForm(request.POST if request.method == 'POST' else None, instance=user)
    if request.method == 'POST' and form.is_valid():
        try:
            services.save_account(form.save(commit=False), form.cleaned_data.get('new_password1'))
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, '账户信息已发生变化，请刷新后重试。')
        else:
            if user.pk == request.user.pk and form.cleaned_data.get('new_password1'):
                update_session_auth_hash(request, user)
            messages.success(request, '账户已更新。')
            return management_redirect(request, 'accounts:list')
    return form_page(request, form, '编辑账户', account=user,
                     note='新密码留空时保留原密码。密码仅能重设，无法查看原密码。')


@administrator_required
@require_POST
def account_bulk(request):
    form = BulkAccountForm(request.POST)
    if form.is_valid():
        try:
            count = services.bulk_accounts(form.cleaned_data['selected'], form.cleaned_data['action'],
                                          form.cleaned_data.get('permission_group'))
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, '账户或权限组已发生变化，请刷新后重试。')
        else:
            if form.cleaned_data['action'] == 'reset':
                current = User.objects.get(pk=request.user.pk)
                update_session_auth_hash(request, current)
            messages.success(request, f'已处理 {count} 个账户。')
            return management_redirect(request, 'accounts:list')
    return render(request, 'accounts/list.html', {
        'users': User.objects.select_related('permission_group').order_by('username'), 'bulk_form': form,
        'selected_ids': request.POST.getlist('selected'),
    })


@administrator_required
@require_POST
def account_status(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    action = request.POST.get('action')
    if action not in {'activate', 'deactivate'}:
        raise PermissionDenied
    user.is_active = action == 'activate'
    try:
        services.save_account(user)
    except ValidationError:
        raise PermissionDenied
    messages.success(request, f'账户 {user.account_id} 已{"启用" if user.is_active else "停用"}。')
    return management_redirect(request, 'accounts:list')


@groups_required
def group_list(request):
    return render(request, 'accounts/groups.html', {
        'groups': PermissionGroup.objects.annotate(member_count=Count('members')),
    })


@groups_required
def group_edit(request, group_id=None):
    group = get_object_or_404(PermissionGroup, pk=group_id) if group_id else None
    form = PermissionGroupForm(request.POST if request.method == 'POST' else None, instance=group)
    if request.method == 'POST' and form.is_valid():
        try:
            services.save_group(form.save(commit=False))
        except ValidationError as exc:
            form.add_error(None, exc)
        except IntegrityError:
            form.add_error(None, '权限组名称已被使用，请刷新后重试。')
        else:
            messages.success(request, '权限组已保存，组内所有账户立即按新权限生效。')
            return management_redirect(request, 'accounts:groups')
    return form_page(request, form, '编辑权限组' if group else '添加权限组', back='accounts:groups')


@groups_required
def group_delete(request, group_id):
    group = get_object_or_404(PermissionGroup, pk=group_id)
    form = GroupDeleteForm(request.POST if request.method == 'POST' else None, group=group)
    if request.method == 'POST' and form.is_valid():
        try:
            services.delete_group(group, form.cleaned_data.get('replacement'))
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, '权限组已删除。')
            return management_redirect(request, 'accounts:groups')
    return form_page(request, form, f'删除权限组：{group.name}', back='accounts:groups',
                     note='删除前将该组全部账户移入所选权限组；不会删除账户。')
