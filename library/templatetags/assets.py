"""Content-versioned static URLs prevent stale assets after local UI edits."""
import hashlib
from pathlib import Path

from django import template
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    source = finders.find(path)
    if source:
        content = Path(source).read_bytes()
    else:
        with staticfiles_storage.open(path, 'rb') as file:
            content = file.read()
    version = hashlib.sha256(content).hexdigest()[:16]
    url = static(path)
    return f'{url}{"&" if "?" in url else "?"}v={version}'
