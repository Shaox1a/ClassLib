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
env_file = ROOT / '.env'
for line in env_file.read_text(encoding='utf-8-sig').splitlines() if env_file.exists() else ():
    if '=' in line and not line.lstrip().startswith('#'):
        name, value = line.split('=', 1)
        env[name] = value.strip().strip('\"\'')
secrets = [v.encode() for k, v in env.items()
           if re.search('KEY|TOKEN|SECRET|PASSWORD|DATABASE_URL', k, re.I) and len(v) > 15]
password = unquote(urlparse(env.get('DATABASE_URL', '')).password or '')
if len(password) > 9:
    secrets.append(password.encode())
paths = ['.env', '.env.production', '.env.local', '.vercel/project.json',
         'deploy-private/data.json', 'db.sqlite3', 'private_files/test.txt', '账户.txt', '账户.md',
         '学生账户.md', 'secret.pem', 'private.key']
for path in paths:
    git('check-ignore', '--quiet', path)
    assert not git('ls-files', '--', path).strip(), f'Sensitive path tracked: {path}'
assert '.env.example' in git('ls-files', '--', '.env.example').decode()

objects = git('rev-list', '--objects', '--all').decode().splitlines()
ids = sorted({line.split(' ', 1)[0] for line in objects})
types = git('cat-file', '--batch-check', input=('\n'.join(ids)+'\n').encode()).decode().splitlines()
blobs = [line.split()[0] for line in types if line.split()[1] == 'blob']
findings = []
pattern = re.compile(
    rb'sb_secret_[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[\w]{35,}'
    rb'|sk-[A-Za-z0-9_-]{25,}|AIza[A-Za-z0-9_-]{35}|AKIA[A-Z0-9]{16}'
    rb'|xox[baprs]-[\w-]{20,}|vcp_[\w-]{28,}|eyJ[\w-]{8,}\.eyJ[\w-]{8,}\.[\w-]{20,}'
    rb'|-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'
)
def inspect(data, label):
    if any(secret in data for secret in secrets) or pattern.search(data):
        findings.append(label)


def private_roster_patterns():
    """Compare the working tree to the private production roster when available."""
    roster = ROOT / '账户.md'
    patterns = []
    production = False
    if roster.exists():
        for line in roster.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('### '):
                production = line.startswith('### 部署端')
            fields = line.split()
            if not production or line.startswith('#') or len(fields) != 3:
                continue
            identity, nickname, password = fields
            patterns.append(re.compile(rb'\s+'.join(re.escape(v.encode()) for v in fields)))
            if identity not in ('root', 'teacher', 'student'):
                for value in (identity, password):
                    patterns.append(re.compile(rb'(?<![\w-])' + re.escape(value.encode()) + rb'(?![\w-])'))
    return patterns


for oid in blobs:
    inspect(git('cat-file', 'blob', oid), 'history-blob:' + oid)
inspect(git('log', '--all', '--format=%B'), 'commit messages')
roster_patterns = private_roster_patterns()
for raw_path in git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0'):
    if raw_path:
        path = ROOT / raw_path.decode()
        if path.is_file():
            data = path.read_bytes()
            label = str(path.relative_to(ROOT))
            inspect(data, label)
            if any(rule.search(data) for rule in roster_patterns):
                findings.append('private roster match: ' + label)
assert not findings, 'Credential matches found in: ' + ', '.join(findings)
print(json.dumps({'ignored_sensitive_paths': len(paths), 'history_blobs_checked': len(blobs),
                  'credential_matches': 0, 'env_example_tracked': True}))
