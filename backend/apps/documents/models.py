"""documents model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Document(Entity):
    storage_provider = models.CharField(max_length=40)
    storage_container = models.CharField(max_length=300, blank=True)
    storage_key = models.TextField()
    original_name = models.TextField(blank=True)
    media_type = models.CharField(max_length=150, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True)
    checksum = models.CharField(max_length=64, blank=True)
    content_verified = models.BooleanField(default=False)

    class Meta:
        app_label = "target_core"


class UploadConfiguration(Entity):
    """uam_user.upload_sys: system upload definitions, not business documents."""
    document_number = models.CharField(max_length=250, blank=True)
    document_type = models.CharField(max_length=150, blank=True)
    storage_key = models.TextField(blank=True)
    public_path = models.TextField(blank=True)
    original_name = models.CharField(max_length=300, blank=True)
    size_text = models.CharField(max_length=20, blank=True)
    uploaded_by_name = models.CharField(max_length=150, blank=True)

    class Meta:
        app_label = "target_core"


class DocumentUsage(Entity):
    lead = models.ForeignKey('target_core.Lead', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Document', 'UploadConfiguration', 'DocumentUsage']
