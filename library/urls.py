from django.urls import path

from . import views


app_name = 'library'

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/new/', views.folder_create, name='folder_create_root'),
    path('folder/<int:folder_id>/', views.folder_detail, name='folder'),
    path('folder/<int:parent_id>/new/', views.folder_create, name='folder_create_child'),
    path('folder/<int:folder_id>/rename/', views.folder_rename, name='folder_rename'),
    path('folder/<int:folder_id>/move/', views.folder_move, name='folder_move'),
    path('folder/<int:folder_id>/delete/', views.folder_delete, name='folder_delete'),
    path('folder/<int:folder_id>/upload/', views.file_upload, name='file_upload'),
    path('file/<int:file_id>/', views.file_detail, name='file'),
    path('file/<int:file_id>/download/', views.file_download, name='file_download'),
    path('file/<int:file_id>/rename/', views.file_rename, name='file_rename'),
    path('file/<int:file_id>/move/', views.file_move, name='file_move'),
    path('file/<int:file_id>/delete/', views.file_delete, name='file_delete'),
    path('file/<int:file_id>/tags/', views.file_tags, name='file_tags'),
    path('search/', views.search, name='search'),
    path('tags/', views.tag_list, name='tags'),
    path('tags/new/', views.tag_create, name='tag_create'),
    path('tags/<int:tag_id>/rename/', views.tag_rename, name='tag_rename'),
    path('tags/<int:tag_id>/delete/', views.tag_delete, name='tag_delete'),
]
