"""Back up current cloud records, then apply the explicitly requested release migration."""
import argparse
from io import StringIO
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['backup', 'migrate'])
action = parser.parse_args().action
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        name, value = line.split('=', 1)
        os.environ[name.strip()] = value.strip().strip('\"\'')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from django.db import connection

directory = ROOT / 'deploy-private' / 'release-1.0'
directory.mkdir(exist_ok=True)
backup = directory / 'cloud-before.json'
def records():
    output = StringIO()
    call_command('dumpdata', natural_foreign=True, natural_primary=True,
                 exclude=['contenttypes', 'auth.permission', 'sessions', 'admin.logentry'], stdout=output)
    return output.getvalue()

if action == 'backup':
    if backup.exists():
        raise RuntimeError('Release backup already exists; refusing to overwrite')
    backup.write_text(records(), encoding='utf-8')
    with connection.cursor() as cursor:
        cursor.execute('select to_jsonb(t) from classlib.library_tag t')
        tags = [row[0] for row in cursor.fetchall()]
        cursor.execute('select to_jsonb(t) from classlib.library_filetag t')
        links = [row[0] for row in cursor.fetchall()]
    (directory / 'removed-tags.json').write_text(json.dumps({'tags': tags, 'links': links}), encoding='utf-8')
    print(f'Cloud records backed up; {len(tags)} tags and {len(links)} links archived')
else:
    assert backup.exists(), 'Run backup before migration'
    call_command('migrate', interactive=False)
    ContentType.objects.filter(app_label='library', model__in=['tag', 'filetag']).delete()
    canonical = lambda text: sorted(json.dumps(row, sort_keys=True) for row in json.loads(text))
    assert canonical(records()) == canonical(backup.read_text(encoding='utf-8')), 'Application records changed'
    with connection.cursor() as cursor:
        cursor.execute("select to_regclass('classlib.library_tag'), to_regclass('classlib.library_filetag')")
        assert cursor.fetchone() == (None, None)
    print('Tag tables removed; all remaining application records unchanged')
