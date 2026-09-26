from django.urls import path

from . import views


app_name = 'library'

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/<int:folder_id>/', views.folder_detail, name='folder'),
    path('file/<int:file_id>/', views.file_detail, name='file'),
    path('search/', views.search, name='search'),
]
