from django.conf import settings
from django.db import models


class SourceModel(models.Model):
    # Each concrete table maps to exactly one documented legacy table.
    source_id = models.CharField(max_length=100, unique=True)
    raw = models.JSONField(default=dict)
    issues = models.JSONField(default=list)
    class Meta:
        abstract = True


class Bank(SourceModel):
    name = models.TextField(blank=True)


class Office(SourceModel):
    name = models.TextField(blank=True)
    branch = models.TextField(blank=True)
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)


class Contact(SourceModel):
    name = models.TextField(blank=True)
    office = models.ForeignKey(Office, null=True, on_delete=models.PROTECT)


class Lead(SourceModel):
    number = models.TextField(blank=True)
    office = models.ForeignKey(Office, null=True, on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, null=True, on_delete=models.PROTECT)
    received_date = models.DateField(null=True, db_index=True)
    status = models.CharField(max_length=40, blank=True)


class Case(SourceModel):
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT, related_name='cases')
    service = models.TextField(blank=True)
    subtype = models.TextField(blank=True)
    district = models.TextField(blank=True)


class SourceRecord(models.Model):
    """Staging for the remaining exported entities, not operational domain models."""
    sheet = models.CharField(max_length=80)
    source_id = models.CharField(max_length=100)
    raw = models.JSONField(default=dict)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['sheet', 'source_id'], name='unique_staged_source')]


class ImportBatch(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=64)
    summary = models.JSONField(default=dict)


class LeadNote(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
