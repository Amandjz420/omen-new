"""audit model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class LeadCounter(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    value = models.PositiveBigIntegerField(default=0)

    class Meta:
        app_label = "target_core"


class LocalRecord(Entity):
    """A reviewed local edit transfers this record's ownership from the importer."""
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()

    class Meta:
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['target_model', 'target_id'], name='local_record_unique')]


class IntakeAudit(Entity):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        app_label = "target_core"


__all__ = ['LocalRecord', 'IntakeAudit', 'LeadCounter']
