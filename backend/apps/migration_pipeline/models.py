"""migration_pipeline model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class ImportBatch(Entity):
    snapshot_checksum = models.CharField(max_length=64)
    conversion_version = models.CharField(max_length=80)
    source_environment = models.CharField(max_length=20)
    status = models.CharField(max_length=30, default='staged')
    summary = models.JSONField(default=dict)

    class Meta:
        app_label = "target_core"


class SourceIdentity(Entity):
    batch = models.ForeignKey('target_core.ImportBatch', on_delete=models.PROTECT)
    environment = models.CharField(max_length=20)
    schema = models.CharField(max_length=80)
    table = models.CharField(max_length=100)
    # Canonical typed JSON for key components, not a concatenation of bare values.
    key = models.CharField(max_length=512)
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()
    class Meta:
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['environment','schema','table','key'], name='source_identity_unique')]


class MigrationIssue(Entity):
    batch = models.ForeignKey('target_core.ImportBatch', on_delete=models.PROTECT)
    source_identity = models.JSONField(default=dict)
    reason = models.TextField()
    resolution = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        app_label = "target_core"


class SourceRow(Entity):
    """Latest source row for replay/quarantine, not a competing business model."""
    schema = models.CharField(max_length=80)
    table = models.CharField(max_length=100)
    key = models.CharField(max_length=512)
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    batch = models.ForeignKey('target_core.ImportBatch', on_delete=models.PROTECT)
    outcome = models.CharField(max_length=30)
    problems = models.JSONField(default=list)
    class Meta:
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['schema','table','key'],name='source_row_unique')]


__all__ = ['ImportBatch', 'SourceIdentity', 'MigrationIssue', 'SourceRow']
