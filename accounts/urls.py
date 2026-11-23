from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


app_name = 'accounts'

urlpatterns = [
    path(
        'login/',
        views.LoginView.as_view(template_name='accounts/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('account/', views.profile, name='profile'),
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
    path('accounts/bulk/', views.account_bulk, name='bulk'),
    path('accounts/<int:user_id>/edit/', views.account_edit, name='edit'),
    path('accounts/<int:user_id>/status/', views.account_status, name='status'),
    path('groups/', views.group_list, name='groups'),
    path('groups/new/', views.group_edit, name='group_create'),
    path('groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),
]
