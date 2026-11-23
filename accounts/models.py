from uuid import uuid4

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def group_key():
    return uuid4().hex


class PermissionGroup(models.Model):
    key = models.CharField(max_length=32, unique=True, default=group_key, editable=False)
    name = models.CharField('名称', max_length=80, unique=True)
    can_view = models.BooleanField('浏览资料', default=False)
    can_download = models.BooleanField('下载文件', default=False)
    can_upload = models.BooleanField('上传文件', default=False)
    can_manage = models.BooleanField('新建、重命名、移动和删除资料', default=False)
    can_manage_accounts = models.BooleanField('管理账户（含重置密码和分配权限组）', default=False)
    can_manage_groups = models.BooleanField('管理权限组', default=False)

    class Meta:
        ordering = ('pk',)
        verbose_name = '权限组'

    def __str__(self):
        return self.name


DEFAULT_GROUPS = {
    'student': dict(name='学生', can_view=True, can_download=True),
    'teacher': dict(name='教师', can_view=True, can_download=True, can_upload=True, can_manage=True),
    'admin': dict(name='管理员', can_view=True, can_download=True, can_upload=True,
                  can_manage=True, can_manage_accounts=True, can_manage_groups=True),
}


class ClassLibUserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        # Keep command-line integrations using the former built-in role names working.
        role = extra_fields.pop('role', 'student')
        if 'permission_group' not in extra_fields and 'permission_group_id' not in extra_fields:
            if role not in DEFAULT_GROUPS:
                raise ValueError('Unknown permission group.')
            extra_fields['permission_group'] = PermissionGroup.objects.get_or_create(
                key=role, defaults=DEFAULT_GROUPS[role],
            )[0]
        return super()._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', '学生'
        TEACHER = 'teacher', '教师'
        ADMIN = 'admin', '管理员'

    nickname = models.CharField('昵称', max_length=150, unique=True)
    permission_group = models.ForeignKey(
        PermissionGroup, verbose_name='权限组', on_delete=models.PROTECT,
        related_name='members',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ClassLibUserManager()

    @property
    def account_id(self):
        return self.username

    @property
    def role(self):
        return self.permission_group.key

    def clean(self):
        super().clean()
        self.nickname = self.normalize_username(self.nickname or self.username).strip()
        others = type(self).objects.exclude(pk=self.pk)
        if others.filter(Q(username=self.nickname) | Q(nickname=self.nickname)).exists():
            raise ValidationError({'nickname': '昵称已被使用，或与其他账户的 ID 重复。'})
        if others.filter(nickname=self.username).exists():
            raise ValidationError({'username': '此 ID 与其他账户的昵称重复。'})

    def save(self, *args, **kwargs):
        if not self.permission_group_id:
            self.permission_group = PermissionGroup.objects.get_or_create(
                key='student', defaults=DEFAULT_GROUPS['student'],
            )[0]
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).values_list('username', flat=True).first()
            if original is not None and self.username != original:
                raise ValidationError('账户 ID 创建后不能修改。')
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nickname
