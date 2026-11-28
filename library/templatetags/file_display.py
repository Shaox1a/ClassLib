from pathlib import PurePosixPath

from django import template

from library.services import preview_format

register = template.Library()

@register.filter
def file_type(name):
    extension = PurePosixPath(name).suffix.lstrip('.').upper()
    return f'{extension} 文件' if extension else '文件'

@register.filter
def is_image_file(document):
    return preview_format(document.name, document.mime_type)[0] == 'image'


@register.filter
def byte_size(value):
    size = int(value)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'):
        if size < 1024 or unit == 'EiB':
            return f'{size:g} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
