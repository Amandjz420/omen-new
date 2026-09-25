"""valuations model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Valuation(Entity):
    """One per case. legacy_status is the live status and holds the legacy text
    values: Pending, Submit, Hold, Cancel, Revert. ValuationStatusEnum gives Hold
    and Cancel the same number, but the source stores names, so nothing is lost.
    Final approval is recorded on ValuationVerification; a completed valuation
    stays Submit."""
    case = models.ForeignKey('target_core.Case', on_delete=models.PROTECT)
    work_order = models.ForeignKey('target_core.WorkOrder', null=True, on_delete=models.PROTECT)
    assessor = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT)
    valuation_date = models.DateField(null=True)
    legacy_status = models.CharField(max_length=80, blank=True)
    report_number = models.CharField(max_length=100, blank=True)
    assessor_name = models.CharField(max_length=200, blank=True)
    submitted_to = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT, related_name='valuations_received')
    liable_employee = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT, related_name='valuations_liable')
    eligible_loan_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    desired_loan_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    total_billing_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    advance_collected = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    remaining_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    total_after_tax = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    total_after_tax_words = models.CharField(max_length=500, blank=True)
    assessor_comment = models.TextField(blank=True)
    non_cost_factor = models.TextField(blank=True)
    REPORT_CATEGORIES = [(1, 'Safe'), (2, 'Risky')]                     # ReportCategoryEnum; 0 means unset
    report_category = models.IntegerField(null=True, choices=REPORT_CATEGORIES)
    dispatch_at_code = models.IntegerField(null=True)
    dispatch_by_code = models.IntegerField(null=True)
    status_reason = models.CharField(max_length=500, blank=True)
    status_reason_date = models.DateField(null=True)
    # The status a hold was placed from, so unholding restores it. The legacy
    # system always unheld to Pending, which would send a held submission back to
    # the assessor. Unknown for the 24 imported holds, which unhold to Pending.
    held_from_status = models.CharField(max_length=80, blank=True)

    class Meta:
        app_label = "target_core"


class ValuationAttachment(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='attachments')
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=500, blank=True)
    attachment_type = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class QuestionCategory(NamedEntity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Question(Entity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    service = models.ForeignKey('target_core.ServiceType', null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    category = models.ForeignKey('target_core.QuestionCategory', null=True, on_delete=models.PROTECT)
    text = models.TextField(blank=True)
    answer_type = models.PositiveSmallIntegerField(null=True)
    question_type = models.PositiveSmallIntegerField(null=True)
    is_document = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)
    display_order = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class QuestionOption(Entity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    question = models.ForeignKey('target_core.Question', on_delete=models.PROTECT, related_name='options')
    value = models.TextField(blank=True)
    value_type = models.CharField(max_length=200, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ValuationAnswer(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='answers')
    question = models.ForeignKey('target_core.Question', on_delete=models.PROTECT)
    option = models.ForeignKey('target_core.QuestionOption', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    answer_group = models.PositiveIntegerField(default=0, db_index=True)
    value = models.TextField(blank=True)
    class Meta:
        app_label = "target_core"
        indexes = [models.Index(fields=['valuation', 'question', 'answer_group'])]


class ValuationVerification(Entity):
    """Five parallel review tracks kept flat, exactly as the source records them.
    Normalizing into one row per track is a later change requiring review."""
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='verifications')
    legal_done_by_name = models.TextField(blank=True)
    legal_date = models.DateField(null=True)
    legal_status = models.CharField(max_length=40, blank=True)
    legal_remark = models.TextField(blank=True)
    technical_done_by_name = models.CharField(max_length=250, blank=True)
    technical_date = models.DateField(null=True)
    technical_status = models.CharField(max_length=40, blank=True)
    technical_remark = models.TextField(blank=True)
    social_done_by_name = models.CharField(max_length=250, blank=True)
    social_date = models.DateField(null=True)
    social_status = models.CharField(max_length=40, blank=True)
    social_remark = models.TextField(blank=True)
    general_done_by_name = models.CharField(max_length=300, blank=True)
    general_date = models.DateField(null=True)
    general_status = models.CharField(max_length=40, blank=True)
    general_remark = models.TextField(blank=True)
    final_done_by_name = models.CharField(max_length=200, blank=True)
    final_status = models.CharField(max_length=100, blank=True)
    # Who acted, by account. Names are not unique; every legacy id resolves.
    legal_done_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    technical_done_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    social_done_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    general_done_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    final_done_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        app_label = "target_core"


class Reversion(Entity):
    """A valuation sent back for correction."""
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='reversions')
    remark = models.CharField(max_length=300, blank=True)
    reverted_on = models.DateField(null=True)
    reverted_by_name = models.CharField(max_length=200, blank=True)
    reverted_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    # Set on reverts made here. The legacy table kept one row per valuation and
    # overwrote it, so only the latest of several reverts survives in the import.
    stage = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ValuationEvent(Entity):
    """A change to a valuation's standing: hold, unhold, cancel, final approval.

    The legacy system kept one reason field on the valuation and overwrote it, so
    only the latest hold or cancellation reason survived. Every change is kept
    here. Sends-back are recorded as Reversion."""
    HOLD, UNHOLD, CANCEL, APPROVE = 'hold', 'unhold', 'cancel', 'approve'
    KINDS = [(HOLD, 'Put on hold'), (UNHOLD, 'Taken off hold'), (CANCEL, 'Cancelled'), (APPROVE, 'Final approval')]
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='events')
    kind = models.CharField(max_length=20, choices=KINDS)
    from_status = models.CharField(max_length=80, blank=True)
    to_status = models.CharField(max_length=80, blank=True)
    reason = models.TextField(blank=True)
    on = models.DateField(null=True)
    by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    by_name = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Valuation', 'QuestionCategory', 'Question', 'QuestionOption', 'ValuationAnswer', 'ValuationVerification', 'Reversion', 'ValuationAttachment', 'ValuationEvent']
