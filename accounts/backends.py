from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import make_password
from django.db.models import Q

from .models import User


class IdentityBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        identity = User.normalize_username(username).strip()
        try:
            user = User.objects.select_related('permission_group').get(
                Q(username=identity) | Q(nickname=identity),
            )
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            make_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

    def get_user(self, user_id):
        try:
            user = User.objects.select_related('permission_group').get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
