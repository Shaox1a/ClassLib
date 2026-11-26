from django.db import migrations, models
from collections import defaultdict


def seed_positions(apps, schema_editor):
    Folder = apps.get_model('library', 'Folder')
    grouped = defaultdict(list)
    for folder in Folder.objects.order_by('name', 'pk'):
        grouped[folder.parent_id].append(folder)
    for folders in grouped.values():
        for index, folder in enumerate(folders):
            folder.position = index
            folder.save(update_fields=['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0005_folder_uploader'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='position',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(seed_positions, migrations.RunPython.noop),
    ]