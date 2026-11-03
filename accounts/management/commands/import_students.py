from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from accounts.models import User


class Command(BaseCommand):
    help = 'Import student accounts from lines formatted as "username password".'

    def add_arguments(self, parser):
        parser.add_argument('source', type=Path, help='UTF-8 text file containing student accounts')
        parser.add_argument('--dry-run', action='store_true', help='Validate without creating accounts')

    def handle(self, *args, **options):
        source = options['source']
        try:
            lines = source.read_text(encoding='utf-8-sig').splitlines()
        except (OSError, UnicodeError) as exc:
            raise CommandError('无法读取账号文件，请检查路径和 UTF-8 编码。') from exc

        rows = []
        seen = set()
        invalid_lines = []
        weak_password_count = 0
        username_field = User._meta.get_field('username')
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            username, separator, password = line.partition(' ')
            if not separator or not username or not password:
                invalid_lines.append(line_number)
                continue
            try:
                username_field.clean(username, None)
            except ValidationError:
                invalid_lines.append(line_number)
                continue
            if username in seen:
                invalid_lines.append(line_number)
                continue
            seen.add(username)
            rows.append((username, password))
            try:
                validate_password(password, user=User(username=username))
            except ValidationError:
                weak_password_count += 1

        if invalid_lines:
            raise CommandError(f'账号文件有格式错误或重复用户名，行号：{invalid_lines}。')
        if not rows:
            raise CommandError('账号文件没有可导入的记录。')

        with transaction.atomic():
            existing = set(User.objects.filter(
                username__in=[username for username, _ in rows]
            ).values_list('username', flat=True))
            if existing:
                raise CommandError(f'数据库中已有 {len(existing)} 个同名账号；未导入任何账号。')
            if not options['dry_run']:
                try:
                    for username, password in rows:
                        User.objects.create_user(
                            username=username,
                            password=password,
                            role=User.Role.STUDENT,
                            is_active=True,
                            is_staff=False,
                            is_superuser=False,
                        )
                except IntegrityError as exc:
                    raise CommandError('导入遇到用户名冲突；本次导入已回滚。') from exc

        label = '预检查通过' if options['dry_run'] else '已创建'
        self.stdout.write(self.style.SUCCESS(f'{label} {len(rows)} 个学生账号。'))
        if weak_password_count:
            self.stdout.write(self.style.WARNING(
                f'其中 {weak_password_count} 个提供的密码未通过 Django 强度校验；已保留原密码。'
            ))
