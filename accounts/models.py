from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class ClassLibUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        if extra_fields['role'] != User.Role.ADMIN:
            raise ValueError('Superusers must have the admin role.')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', '学生'
        TEACHER = 'teacher', '教师'
        ADMIN = 'admin', '管理员'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ClassLibUserManager()

    def __str__(self):
        return self.username
