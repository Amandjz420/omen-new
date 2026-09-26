"""dispatch model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Dispatch(Entity):
    MODES = [(1, 'Courier'), (2, 'Speed Post'), (3, 'By Hand'), (4, 'Pick up from HO'),
             (5, 'By E-Mail'), (6, 'Normal Post')]                     # ModeOfDispatchEnum
    STATUSES = [(1, 'Lying at HO'), (2, 'Under Transit'), (3, 'Delivered')]  # DispatchStatusEnum
    COURIERS = [(1, 'Madhur Courier Services'), (2, 'India Post Services'), (3, 'Other')]  # CourierByEnum

    number = models.CharField(max_length=50, db_index=True)
    client_name = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    town = models.CharField(max_length=255, blank=True)
    document_count = models.IntegerField(null=True)
    report_references = models.CharField(max_length=500, blank=True)
    other_documents = models.CharField(max_length=500, blank=True)
    mode = models.IntegerField(null=True, choices=MODES)
    status = models.IntegerField(null=True, choices=STATUSES)
    courier = models.IntegerField(null=True, choices=COURIERS)
    other_courier = models.CharField(max_length=500, blank=True)
    consignment_number = models.CharField(max_length=500, blank=True)
    authorized_person = models.CharField(max_length=500, blank=True)
    cost = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    outward_date = models.DateField(null=True)
    filter_date = models.DateField(null=True)
    delivered_date = models.DateField(null=True)
    cancelled = models.BooleanField(default=False)
    cancel_remark = models.TextField(blank=True)

    # Dispatches made here. request_key makes creation retry-safe; local_sequence is
    # the number's counter.
    local_sequence = models.PositiveBigIntegerField(null=True, blank=True, unique=True, editable=False)
    request_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    request_hash = models.CharField(max_length=64, blank=True, editable=False)
    created_by = models.ForeignKey('target_core.LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    created_by_name = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = "target_core"


class DispatchItem(Entity):
    """One report reference within a dispatch, with its resolution recorded."""
    EXACT, NORMALIZED, LEAD_NUMBER, UNRESOLVED, CHOSEN = 'exact', 'normalized', 'lead_number', 'unresolved', 'chosen'
    RESOLUTIONS = [(CHOSEN, 'Chosen here from the reports awaiting dispatch'),
                   (EXACT, 'Matched a report number exactly'),
                   (NORMALIZED, 'Matched after correcting spacing, hyphen or prefix'),
                   (LEAD_NUMBER, 'A lead number entered where a report number belongs'),
                   (UNRESOLVED, 'No valuation carries this report number')]

    dispatch = models.ForeignKey('target_core.Dispatch', on_delete=models.PROTECT, related_name='items')
    position = models.PositiveIntegerField()
    reference = models.CharField(max_length=100)
    valuation = models.ForeignKey('Valuation', null=True, on_delete=models.PROTECT, related_name='dispatch_items')
    lead = models.ForeignKey('target_core.Lead', null=True, on_delete=models.PROTECT)
    resolution = models.CharField(max_length=20, choices=RESOLUTIONS)
    # Set when a report already dispatched is deliberately sent again; 356 approved
    # reports appear in more than one legacy dispatch, with nothing to say why.
    # The report revision this item sent. Report numbers stay the same across
    # revisions, so without it an older revision's dispatch hid a corrected one from
    # the awaiting queue (review N3). Empty on items from the previous system, which
    # recorded no revision.
    bank_report = models.ForeignKey('target_core.BankReport', null=True, blank=True, on_delete=models.PROTECT, related_name='dispatch_items')
    resend = models.BooleanField(default=False)
    resend_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['dispatch', 'position'], name='dispatch_item_position')]


class SmsMessage(Entity):
    """lead_mngt.sms_log. Historical evidence; the new system sends nothing."""
    reference_client_id = models.CharField(max_length=100, blank=True)
    record_id = models.IntegerField(null=True)
    mobile = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    client_type = models.CharField(max_length=100, blank=True)
    template_id = models.CharField(max_length=100, blank=True)
    sender_id = models.CharField(max_length=100, blank=True)
    response_code = models.CharField(max_length=100, blank=True)
    response_message = models.TextField(blank=True)
    delivery_report = models.CharField(max_length=100, blank=True)
    request_reference = models.CharField(max_length=100, blank=True)
    gateway_transaction = models.CharField(max_length=100, blank=True)
    sent_at = models.DateTimeField(null=True, db_index=True)
    server_ip_address = models.CharField(max_length=100, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Dispatch', 'DispatchItem', 'SmsMessage']
