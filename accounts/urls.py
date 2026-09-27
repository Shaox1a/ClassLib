from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = 'accounts'

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='accounts/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(
            template_name='accounts/password_change.html',
            success_url='/password/changed/',
        ),
        name='password_change',
    ),
    path(
        'password/changed/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_changed.html',
        ),
        name='password_changed',
    ),
    path('accounts/', views.account_list, name='list'),
    path('accounts/new/', views.account_create, name='create'),
    path('accounts/<int:user_id>/status/', views.account_status, name='status'),
]
