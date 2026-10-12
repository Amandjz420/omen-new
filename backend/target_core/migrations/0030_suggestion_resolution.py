from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('target_core', '0029_assistsource_suggestion')]
    operations = [
        migrations.AddField(model_name='suggestion', name='resolution', field=models.CharField(max_length=20, blank=True)),
        migrations.AddField(model_name='suggestion', name='previous_answer', field=models.JSONField(default=dict, blank=True)),
    ]
