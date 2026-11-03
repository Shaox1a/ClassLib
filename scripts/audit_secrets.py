"""Check ignore rules and Git blobs without printing credential values."""
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
def git(*args, input=None):
    return subprocess.check_output(['git', *args], cwd=ROOT, input=input)

env = {}
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        name, value = line.split('=', 1)
        env[name] = value.strip().strip('\"\'')
secrets = [v.encode() for k, v in env.items() if ('KEY' in k or k == 'DATABASE_URL') and len(v) > 15]
password = unquote(urlparse(env.get('DATABASE_URL', '')).password or '')
if len(password) > 9:
    secrets.append(password.encode())
paths = ['.env', '.env.production', '.env.local', '.vercel/project.json',
         'deploy-private/data.json', 'db.sqlite3', 'private_files/test.txt', '账户.txt']
for path in paths:
    git('check-ignore', '--quiet', path)
    assert not git('ls-files', '--', path).strip(), f'Sensitive path tracked: {path}'
assert '.env.example' in git('ls-files', '--', '.env.example').decode()

objects = git('rev-list', '--objects', '--all').decode().splitlines()
ids = sorted({line.split(' ', 1)[0] for line in objects})
types = git('cat-file', '--batch-check', input=('\n'.join(ids)+'\n').encode()).decode().splitlines()
blobs = [line.split()[0] for line in types if line.split()[1] == 'blob']
findings = []
pattern = re.compile(rb'sb_secret_[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
def inspect(data, label):
    if any(secret in data for secret in secrets) or pattern.search(data):
        findings.append(label)
for oid in blobs:
    inspect(git('cat-file', 'blob', oid), 'history-blob:' + oid)
for raw_path in git('ls-files', '-z').split(b'\0'):
    if raw_path:
        path = ROOT / raw_path.decode()
        if path.is_file():
            inspect(path.read_bytes(), str(path.relative_to(ROOT)))
assert not findings, 'Credential matches found in: ' + ', '.join(findings)
print(json.dumps({'ignored_sensitive_paths': len(paths), 'history_blobs_checked': len(blobs),
                  'credential_matches': 0, 'env_example_tracked': True}))
