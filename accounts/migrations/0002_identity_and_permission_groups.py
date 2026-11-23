import accounts.models
import django.db.models.deletion
from django.db import migrations, models


def populate(apps, schema_editor):
    Group = apps.get_model('accounts', 'PermissionGroup')
    User = apps.get_model('accounts', 'User')
    database = schema_editor.connection.alias
    defaults = {
        'student': dict(name='学生', can_view=True, can_download=True),
        'teacher': dict(name='教师', can_view=True, can_download=True, can_upload=True, can_manage=True),
        'admin': dict(name='管理员', can_view=True, can_download=True, can_upload=True,
                      can_manage=True, can_manage_accounts=True, can_manage_groups=True),
    }
    groups = {key: Group.objects.using(database).create(key=key, **values) for key, values in defaults.items()}
    for user in User.objects.using(database).all().iterator():
        group = groups['admin'] if user.is_superuser else groups.get(user.role, groups['student'])
        User.objects.using(database).filter(pk=user.pk).update(nickname=user.username, permission_group_id=group.pk)
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('ALTER TABLE accounts_permissiongroup ENABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='PermissionGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(default=accounts.models.group_key, editable=False, max_length=32, unique=True)),
                ('name', models.CharField(max_length=80, unique=True, verbose_name='名称')),
                ('can_view', models.BooleanField(default=False, verbose_name='浏览资料')),
                ('can_download', models.BooleanField(default=False, verbose_name='下载文件')),
                ('can_upload', models.BooleanField(default=False, verbose_name='上传文件')),
                ('can_manage', models.BooleanField(default=False, verbose_name='新建、重命名、移动和删除资料')),
                ('can_manage_accounts', models.BooleanField(default=False, verbose_name='管理账户（含重置密码和分配权限组）')),
                ('can_manage_groups', models.BooleanField(default=False, verbose_name='管理权限组')),
            ],
            options={'ordering': ('pk',), 'verbose_name': '权限组'},
        ),
        migrations.AddField(model_name='user', name='nickname', field=models.CharField(max_length=150, null=True, verbose_name='昵称')),
        migrations.AddField(model_name='user', name='permission_group', field=models.ForeignKey(
            null=True, on_delete=django.db.models.deletion.PROTECT, related_name='members', to='accounts.permissiongroup', verbose_name='权限组')),
        migrations.RunPython(populate, migrations.RunPython.noop),
        migrations.AlterField(model_name='user', name='nickname', field=models.CharField(max_length=150, unique=True, verbose_name='昵称')),
        migrations.AlterField(model_name='user', name='permission_group', field=models.ForeignKey(
            on_delete=django.db.models.deletion.PROTECT,
            related_name='members', to='accounts.permissiongroup', verbose_name='权限组')),
        migrations.RemoveField(model_name='user', name='role'),
    ]
