from pathlib import PurePosixPath

from django import forms
from django.core.exceptions import ValidationError

from .models import File, Folder
from .services import descendant_folder_ids


def clean_display_name(name):
    name = name.strip()
    if not name or name in {'.', '..'} or '/' in name or '\\' in name or any(ord(char) < 32 for char in name):
        raise ValidationError('请输入有效名称。')
    return name



class FolderNameForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name',)

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent if not self.instance.pk else self.instance.parent

    def clean_name(self):
        name = clean_display_name(self.cleaned_data['name'])
        siblings = Folder.objects.filter(name=name, parent=self.parent)
        if self.instance.pk:
            siblings = siblings.exclude(pk=self.instance.pk)
        if siblings.exists():
            raise ValidationError('这个位置已有同名文件夹。')
        return name


class FolderMoveForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Folder.objects.all(), required=False, label='目标文件夹', empty_label='根目录'
    )

    class Meta:
        model = Folder
        fields = ('parent',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['parent'].queryset = Folder.objects.exclude(
                pk__in=descendant_folder_ids(self.instance)
            )

    def clean_parent(self):
        parent = self.cleaned_data['parent']
        if parent and Folder.objects.filter(name=self.instance.name, parent=parent).exclude(
            pk=self.instance.pk
        ).exists():
            raise ValidationError('目标位置已有同名文件夹。')
        if parent is None and Folder.objects.filter(name=self.instance.name, parent__isnull=True).exclude(
            pk=self.instance.pk
        ).exists():
            raise ValidationError('根目录已有同名文件夹。')
        return parent


class UploadForm(forms.Form):
    upload = forms.FileField(allow_empty_file=True, label='选择文件')

    def __init__(self, *args, folder, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder = folder
        self.file_name = None

    def clean_upload(self):
        uploaded = self.cleaned_data['upload']
        name = clean_display_name(uploaded.name.replace('\\', '/').split('/')[-1])
        if len(name) > 255:
            raise ValidationError('文件名不能超过 255 个字符。')
        if File.objects.filter(folder=self.folder, name=name).exists():
            raise ValidationError('这个文件夹已有同名文件。')
        self.file_name = name
        return uploaded


class FileNameForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ('name',)

    def clean_name(self):
        name = clean_display_name(self.cleaned_data['name'])
        if PurePosixPath(name).suffix.lower() != PurePosixPath(self.instance.name).suffix.lower():
            raise ValidationError('重命名时不能更改文件扩展名。')
        if File.objects.filter(folder=self.instance.folder, name=name).exclude(
            pk=self.instance.pk
        ).exists():
            raise ValidationError('这个文件夹已有同名文件。')
        return name


class FileMoveForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ('folder',)

    def clean_folder(self):
        folder = self.cleaned_data['folder']
        if File.objects.filter(folder=folder, name=self.instance.name).exclude(
            pk=self.instance.pk
        ).exists():
            raise ValidationError('目标文件夹已有同名文件。')
        return folder
