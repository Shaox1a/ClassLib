from django.db import migrations, models
from django.db.models import F

def backfill(apps, schema_editor):
    apps.get_model('library', 'Folder').objects.using(schema_editor.connection.alias).update(updated_at=F('created_at'))

class Migration(migrations.Migration):
    dependencies = [('library', '0003_remove_tags')]
    operations = [
        migrations.AddField(model_name='folder', name='updated_at', field=models.DateTimeField(null=True)),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField(model_name='folder', name='updated_at', field=models.DateTimeField(auto_now=True)),
    ]
