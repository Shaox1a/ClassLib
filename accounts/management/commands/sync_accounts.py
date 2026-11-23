"""Explicit, atomic account replacement from the private account roster."""
from pathlib import Path

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import ProtectedError

from accounts.models import DEFAULT_GROUPS, PermissionGroup, User
from accounts.services import lock_groups, require_administrator


def read_roster(source, environment):
    try:
        lines = source.read_text(encoding='utf-8-sig').splitlines()
    except (OSError, UnicodeError) as exc:
        raise CommandError('无法读取账户清单，请检查路径和 UTF-8 编码。') from exc
    section = role = None
    rows = []
    identifiers, nicknames = set(), set()
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if line.startswith('### 本地端'):
            section, role = 'local', None
        elif line.startswith('### 部署端'):
            section, role = 'production', None
        elif line.startswith('#### '):
            role = next((key for key, label in [('student', '学生'), ('teacher', '教师'), ('admin', '管理员')]
                         if label in line), None)
        elif line and not line.startswith('#') and section == environment:
            parts = line.split()
            if len(parts) != 3:
                raise CommandError(f'清单第 {number} 行应为 ID、昵称、密码三列。')
            identity, nickname, password = parts
            identity = User.normalize_username(identity)
            nickname = User.normalize_username(nickname)
            row_role = role or {'root': 'admin', 'student': 'student', 'teacher': 'teacher'}.get(identity)
            if row_role is None:
                raise CommandError(f'清单第 {number} 行缺少权限组标题。')
            try:
                User._meta.get_field('username').clean(identity, None)
                User._meta.get_field('nickname').clean(nickname, None)
            except ValidationError as exc:
                raise CommandError(f'清单第 {number} 行的 ID 或昵称格式无效。') from exc
            if identity in identifiers or nickname in nicknames:
                raise CommandError(f'清单第 {number} 行的 ID 或昵称重复。')
            identifiers.add(identity)
            nicknames.add(nickname)
            rows.append((identity, nickname, password, row_role))
    if not rows:
        raise CommandError('该环境没有可导入的账户。')
    for identity, nickname, _, _ in rows:
        if any(other_id != identity and (other_id == nickname or other_nick == identity)
               for other_id, other_nick, _, _ in rows):
            raise CommandError('清单中昵称与其他账户 ID 重复，无法唯一登录。')
    if not any(role == 'admin' for _, _, _, role in rows):
        raise CommandError('清单必须包含管理员账户；尚未修改任何账户。')
    return rows


class Command(BaseCommand):
    help = 'Replace accounts using the selected environment section of a private Markdown roster.'

    def add_arguments(self, parser):
        parser.add_argument('source', type=Path)
        parser.add_argument('--environment', choices=('local', 'production'), required=True)
        parser.add_argument('--replace', action='store_true', help='Required to write changes')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        environment = options['environment']
        engine = settings.DATABASES['default']['ENGINE']
        if environment == 'local' and engine != 'django.db.backends.sqlite3':
            raise CommandError('本地账户清单只能写入 SQLite，拒绝修改远程数据库。')
        if environment == 'production' and engine != 'django.db.backends.postgresql':
            raise CommandError('部署端清单只能用于明确配置的 PostgreSQL 数据库。')
        rows = read_roster(options['source'], environment)
        if options['dry_run']:
            self.stdout.write(f'清单验证通过：{len(rows)} 个账户；未写入。')
            return
        if not options['replace']:
            raise CommandError('请指定 --replace 才能替换账户，或使用 --dry-run 检查。')
        try:
            with transaction.atomic():
                lock_groups()
                groups = {key: PermissionGroup.objects.get_or_create(key=key, defaults=values)[0]
                          for key, values in DEFAULT_GROUPS.items()}
                obsolete = User.objects.exclude(username__in=[row[0] for row in rows])
                # Protected file ownership must never be silently reassigned.
                obsolete.delete()
                # Clear mutable names first so an authorized nickname swap is possible.
                for user in User.objects.all():
                    User.objects.filter(pk=user.pk).update(nickname=f'__sync_{user.pk}__')
                for identity, nickname, password, role in rows:
                    user = User.objects.filter(username=identity).first() or User(username=identity)
                    user.nickname = nickname
                    user.permission_group = groups[role]
                    user.is_active = True
                    user.is_staff = user.is_superuser = role == 'admin'
                    user.set_password(password)
                    user.save()
                require_administrator()
                Session.objects.all().delete()
        except ProtectedError as exc:
            raise CommandError('清单外账户仍有上传文件，不能删除；全部变更已回滚，请先确定这些资料的归属。') from exc
        except ValidationError as exc:
            raise CommandError('清单或现有权限组不符合要求，全部变更已回滚：' + '；'.join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f'已替换为 {len(rows)} 个账户，旧登录会话已清除。'))
