import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('target_core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='clientoffice',
            name='district',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='clientoffice',
            name='state',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.CreateModel(
            name='LeadNote',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('body', models.TextField(max_length=4000)),
                ('prototype_note_id', models.BigIntegerField(null=True, unique=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('lead', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='notes', to='target_core.lead')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SourceRow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('schema', models.CharField(max_length=80)),
                ('table', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=512)),
                ('payload', models.JSONField(default=dict)),
                ('payload_hash', models.CharField(max_length=64)),
                ('outcome', models.CharField(max_length=30)),
                ('problems', models.JSONField(default=list)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='target_core.importbatch')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('schema', 'table', 'key'), name='source_row_unique')],
            },
        ),
    ]
