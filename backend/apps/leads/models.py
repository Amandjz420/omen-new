"""leads model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Lead(Entity):
    intake_key = models.UUIDField(null=True, unique=True, editable=False)
    intake_hash = models.CharField(max_length=64, blank=True, editable=False)
    local_sequence = models.PositiveBigIntegerField(null=True, unique=True, editable=False)
    number = models.CharField(max_length=100, blank=True, db_index=True)
    office = models.ForeignKey('target_core.ClientOffice', on_delete=models.PROTECT)
    contact = models.ForeignKey('target_core.Contact', null=True, on_delete=models.PROTECT)
    assigned_employee = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT)
    received_date = models.DateField(null=True, db_index=True)
    date_basis = models.CharField(max_length=40, default='unknown')
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)
    ENQUIRY_MODES = [(1, 'Phone'), (2, 'Email'), (3, 'Online'), (4, 'Walk In'), (5, 'Letter')]  # ModeEnum
    enquiry_mode = models.IntegerField(null=True, choices=ENQUIRY_MODES)
    # The number of parties the enquiry declared. The legacy work-order screen was
    # meant to close a lead once every party had a work order.
    party_count = models.PositiveIntegerField(null=True)
    case_count = models.PositiveIntegerField(null=True)
    received_by = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT, related_name='leads_received')
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    legacy_number_old = models.CharField(max_length=45, blank=True)

    class Meta:
        app_label = "target_core"


class RequestedService(Entity):
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT)
    service = models.ForeignKey('target_core.ServiceType', on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    party_count = models.PositiveIntegerField(null=True)
    case_count = models.PositiveIntegerField(null=True)

    class Meta:
        app_label = "target_core"


class Borrower(NamedEntity):
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT)
    agreed_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    currency = models.CharField(max_length=3, blank=True)
    property_count = models.PositiveIntegerField(null=True)
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=100, blank=True)
    # Who is responsible for the fee, decoded from the legacy enums named beside
    # each set of choices. These print on the work order.
    PAYERS = [(1, 'By Client'), (2, 'By Client Customer')]                  # PaidByEnum
    FEE_BASES = [(1, 'By Circular'), (2, 'By Fixed')]                        # PaymentByEnum
    CUSTOMER_METHODS = [(1, 'By Bank'), (2, 'By Cash'), (3, 'By Any Other')]  # PaidByModeEnum
    payer = models.IntegerField(null=True, choices=PAYERS)
    fee_basis = models.IntegerField(null=True, choices=FEE_BASES)
    customer_payment_method = models.IntegerField(null=True, choices=CUSTOMER_METHODS)
    payer_name = models.CharField(max_length=500, blank=True)
    payer_mobile = models.CharField(max_length=30, blank=True)
    pay_by_date = models.DateField(null=True)
    gst_number = models.CharField(max_length=200, blank=True)
    payment_reference_number = models.CharField(max_length=15, blank=True)
    payment_reference_name = models.CharField(max_length=105, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Case(Entity):
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT)
    borrower = models.ForeignKey('target_core.Borrower', on_delete=models.PROTECT)
    service = models.ForeignKey('target_core.ServiceType', on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    asset_address = models.TextField(blank=True)
    asset_district = models.CharField(max_length=150, blank=True)
    asset_state = models.CharField(max_length=150, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    asset_pin_code = models.CharField(max_length=15, blank=True)
    asset_block_code = models.CharField(max_length=20, blank=True)
    asset_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    contact_person_name = models.CharField(max_length=500, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    expected_report_date = models.DateField(null=True)
    remarks = models.TextField(blank=True)
    # Stored as the legacy codes; they resolve to ReportUsage and
    # ScrutinyRequirement and are linked when the valuation stage uses them.
    usage_of_report_code = models.CharField(max_length=500, blank=True)
    scrutiny_document_code = models.CharField(max_length=500, blank=True)

    class Meta:
        app_label = "target_core"


class LeadNote(Entity):
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)
    prototype_note_id = models.BigIntegerField(null=True, unique=True)

    class Meta:
        app_label = "target_core"


class FollowUp(Entity):
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT, related_name='follow_ups')
    call_status = models.CharField(max_length=50, blank=True)
    logged_date_text = models.CharField(max_length=50, blank=True)
    logged_time_text = models.CharField(max_length=20, blank=True)
    remark = models.TextField(blank=True)
    legacy_update_date = models.CharField(max_length=45, blank=True)

    class Meta:
        app_label = "target_core"


class LeadParty(Entity):
    lead = models.ForeignKey('target_core.Lead', null=True, on_delete=models.PROTECT)
    borrower_name = models.CharField(max_length=300, blank=True)
    contact_person_name = models.CharField(max_length=300, blank=True)
    contact_number = models.CharField(max_length=80, blank=True)

    class Meta:
        app_label = "target_core"


class LeadAttachment(Entity):
    lead = models.ForeignKey('target_core.Lead', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    attachment_type = models.CharField(max_length=40, blank=True)
    remark = models.TextField(blank=True)
    proposal_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Lead', 'RequestedService', 'Borrower', 'Case', 'LeadNote', 'FollowUp', 'LeadParty', 'LeadAttachment']
