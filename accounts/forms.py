from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import PermissionGroup, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='ID / 昵称', max_length=150,
                               widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}))


class PasswordFields(forms.Form):
    new_password1 = forms.CharField(label='新密码', required=False, strip=False,
                                   widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    new_password2 = forms.CharField(label='确认新密码', required=False, strip=False,
                                   widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean(self):
        data = super().clean()
        first, second = data.get('new_password1'), data.get('new_password2')
        if first or second:
            if first != second:
                self.add_error('new_password2', '两次密码不一致。')
        return data

    def _post_clean(self):
        super()._post_clean()
        # ModelForm has now copied the submitted ID/nickname into the instance.
        if password := self.cleaned_data.get('new_password1'):
            try:
                validate_password(password, self.instance)
            except ValidationError as exc:
                self.add_error('new_password1', exc)


class ProfileForm(PasswordFields, forms.ModelForm):
    current_password = forms.CharField(label='当前密码（修改密码时填写）', required=False, strip=False,
                                      widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))

    class Meta:
        model = User
        fields = ('nickname',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(('nickname', 'current_password', 'new_password1', 'new_password2'))

    def clean(self):
        data = super().clean()
        if data.get('new_password1') and not self.instance.check_password(data.get('current_password') or ''):
            self.add_error('current_password', '当前密码不正确。')
        return data


class AccountEditForm(PasswordFields, forms.ModelForm):
    class Meta:
        model = User
        fields = ('nickname', 'permission_group', 'is_active')
        labels = {'is_active': '启用账户'}


class AccountCreationForm(PasswordFields, forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'nickname', 'permission_group')
        labels = {'username': 'ID（创建后不可修改）'}
        help_texts = {'username': '只能使用字母、数字和 @ . + - _。',
                      'nickname': '昵称须唯一，也不能与其他账户的 ID 重复。'}


class BulkAccountForm(forms.Form):
    selected = forms.ModelMultipleChoiceField(queryset=User.objects.all(), label='所选账户')
    action = forms.ChoiceField(label='批量操作', choices=(('reset', '密码重置为各自 ID'), ('move', '移至权限组')))
    permission_group = forms.ModelChoiceField(queryset=PermissionGroup.objects.all(), label='目标权限组', required=False)

    def clean(self):
        data = super().clean()
        if data.get('action') == 'move' and not data.get('permission_group'):
            self.add_error('permission_group', '请选择目标权限组。')
        return data


class PermissionGroupForm(forms.ModelForm):
    class Meta:
        model = PermissionGroup
        fields = ('name', 'can_view', 'can_download', 'can_upload', 'can_manage',
                  'can_manage_accounts', 'can_manage_groups')


class GroupDeleteForm(forms.Form):
    replacement = forms.ModelChoiceField(queryset=PermissionGroup.objects.none(), required=False, label='将组内账户移至')

    def __init__(self, *args, group, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['replacement'].queryset = PermissionGroup.objects.exclude(pk=group.pk)
        self.fields['replacement'].required = group.members.exists()
