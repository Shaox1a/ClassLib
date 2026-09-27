from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import File, Folder, Tag
from .services import descendant_folder_ids


ALLOWED_EXTENSIONS = {
    '.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.txt',
}
OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def clean_display_name(name):
    name = name.strip()
    if not name or name in {'.', '..'} or '/' in name or '\\' in name or any(ord(char) < 32 for char in name):
        raise ValidationError('请输入有效名称。')
    return name


def validate_file_content(uploaded_file, extension):
    uploaded_file.seek(0)
    head = uploaded_file.read(4096)
    try:
        if extension == '.pdf':
            valid = head.startswith(b'%PDF-')
        elif extension in {'.doc', '.ppt', '.xls'}:
            valid = head.startswith(OLE_SIGNATURE)
        elif extension == '.png':
            valid = head.startswith(b'\x89PNG\r\n\x1a\n')
        elif extension in {'.jpg', '.jpeg'}:
            valid = head.startswith(b'\xff\xd8\xff')
        elif extension == '.gif':
            valid = head.startswith((b'GIF87a', b'GIF89a'))
        elif extension == '.webp':
            valid = head[:4] == b'RIFF' and head[8:12] == b'WEBP'
        elif extension == '.txt':
            valid = b'\x00' not in head
        else:
            try:
                with ZipFile(uploaded_file) as archive:
                    if extension == '.zip':
                        valid = True
                    else:
                        names = archive.namelist()
                        prefix = {'.docx': 'word/', '.pptx': 'ppt/', '.xlsx': 'xl/'}[extension]
                        valid = '[Content_Types].xml' in names and any(
                            item.startswith(prefix) for item in names
                        )
            except (BadZipFile, OSError, RuntimeError, ValueError):
                valid = False
        if not valid:
            raise ValidationError('文件内容与扩展名不符，或文件已损坏。')
    finally:
        uploaded_file.seek(0)


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
    upload = forms.FileField(label='选择文件')

    def __init__(self, *args, folder, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder = folder
        self.file_name = None

    def clean_upload(self):
        uploaded = self.cleaned_data['upload']
        name = clean_display_name(uploaded.name.replace('\\', '/').split('/')[-1])
        if len(name) > 255:
            raise ValidationError('文件名不能超过 255 个字符。')
        extension = PurePosixPath(name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationError('不支持这种文件类型。')
        if uploaded.size > settings.MAX_UPLOAD_SIZE:
            raise ValidationError('文件不能超过 50 MiB。')
        if File.objects.filter(folder=self.folder, name=name).exists():
            raise ValidationError('这个文件夹已有同名文件。')
        validate_file_content(uploaded, extension)
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


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ('name',)

    def clean_name(self):
        name = clean_display_name(self.cleaned_data['name'].lstrip('#').strip())
        existing = Tag.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError('这个标签已存在。')
        return name


class FileTagsForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label='标签',
        widget=forms.CheckboxSelectMultiple,
    )
