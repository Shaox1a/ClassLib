from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AccountCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        label='角色',
        choices=[(User.Role.STUDENT, '学生'), (User.Role.TEACHER, '教师')],
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'role')
