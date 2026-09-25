"""reports model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class BankReport(Entity):
    """lead_mngt.valuation_bank_report: the assessed values a valuation produces.

    This is valuation substance, not report formatting, despite the source
    catalogue filing it under reports. Amount words and the certificate text are
    retained as recorded; no amount is recomputed or derived from another.
    """
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='bank_reports')
    bank = models.ForeignKey('target_core.Bank', null=True, on_delete=models.PROTECT)
    branch = models.ForeignKey('target_core.BankBranch', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    report_number = models.CharField(max_length=45, blank=True)
    report_date = models.DateField(null=True)
    our_reference = models.CharField(max_length=50, blank=True)
    your_reference = models.CharField(max_length=150, blank=True)
    omen_id = models.CharField(max_length=50, blank=True)
    unique_reference = models.CharField(max_length=50, blank=True)
    market_fair_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    realisable_value_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    book_value_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    distress_value_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    market_fair_amount_word = models.CharField(max_length=400, blank=True)
    realisable_value_amount_word = models.CharField(max_length=400, blank=True)
    book_value_amount_word = models.CharField(max_length=400, blank=True)
    distress_value_amount_word = models.CharField(max_length=400, blank=True)
    bank_certificate = models.TextField(blank=True)
    legacy_liable_fa = models.CharField(max_length=40, blank=True)
    # Versions. The legacy system kept one report per valuation, updated it in
    # place and deleted it on a final revert, so a report a bank had received
    # could vanish. Here a final revert supersedes the current version instead,
    # and the next one carries the following revision number.
    revision = models.PositiveIntegerField(default=0)
    superseded_at = models.DateTimeField(null=True, blank=True)
    template = models.ForeignKey('ReportTemplate', null=True, blank=True, on_delete=models.PROTECT)
    generated_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    generated_by_name = models.CharField(max_length=200, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    # Set at final approval, when the report is issued to the bank. Only an issued
    # report is superseded by a final revert; an unissued draft is revised in place.
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "target_core"


class ReportTemplate(Entity):
    """lead_mngt.report_setup."""
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    service = models.ForeignKey('target_core.ServiceType', null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey('target_core.Bank', null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ReportHeading(NamedEntity):
    """lead_mngt.bank_report_heading: a section heading within a bank report."""
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey('target_core.Bank', null=True, on_delete=models.PROTECT)
    display_order = models.IntegerField(null=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ReportTemplateLine(Entity):
    """lead_mngt.report_question: one question placed onto a template."""
    template = models.ForeignKey('target_core.ReportTemplate', on_delete=models.PROTECT, related_name='lines')
    question = models.ForeignKey('target_core.Question', null=True, on_delete=models.PROTECT)
    heading = models.ForeignKey('target_core.ReportHeading', null=True, on_delete=models.PROTECT)
    output_label = models.CharField(max_length=1000, blank=True)
    content_before = models.CharField(max_length=500, blank=True)
    content_after = models.CharField(max_length=500, blank=True)
    sequence = models.IntegerField(null=True)
    indexing = models.CharField(max_length=10, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['BankReport', 'ReportTemplate', 'ReportHeading', 'ReportTemplateLine']
