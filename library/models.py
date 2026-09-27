from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class Folder(models.Model):
    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children', on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name', 'pk')
        constraints = [
            models.UniqueConstraint(
                fields=('name',), condition=Q(parent__isnull=True), name='unique_root_folder_name'
            ),
            models.UniqueConstraint(
                fields=('parent', 'name'), condition=Q(parent__isnull=False),
                name='unique_child_folder_name',
            ),
        ]

    def clean(self):
        super().clean()
        if self.parent_id is None:
            return
        ancestor = self.parent
        visited = set()
        while ancestor is not None:
            if ancestor.pk == self.pk or ancestor.pk in visited:
                raise ValidationError({'parent': '不能将文件夹移入自身或其子文件夹。'})
            visited.add(ancestor.pk)
            ancestor = ancestor.parent

    def __str__(self):
        return self.name

    @property
    def path(self):
        names = []
        folder = self
        while folder is not None:
            names.append(folder.name)
            folder = folder.parent
        return ' / '.join(reversed(names))


class File(models.Model):
    name = models.CharField(max_length=255)
    folder = models.ForeignKey(Folder, related_name='files', on_delete=models.CASCADE)
    storage_key = models.CharField(max_length=255, unique=True)
    size = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=120)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='uploaded_files', on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField('Tag', through='FileTag', related_name='files', blank=True)

    class Meta:
        ordering = ('name', 'pk')
        constraints = [
            models.UniqueConstraint(fields=('folder', 'name'), name='unique_file_name_per_folder')
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=40)

    class Meta:
        ordering = ('name', 'pk')
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_tag_name_case_insensitive')
        ]

    def __str__(self):
        return self.name


class FileTag(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='tag_links')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='file_links')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('file', 'tag'), name='unique_file_tag')
        ]
