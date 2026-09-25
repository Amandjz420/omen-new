"""workorders model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class WorkOrder(Entity):
    """A work order is issued per borrower, not per lead (legacy lead_order)."""
    lead = models.ForeignKey('target_core.Lead', on_delete=models.PROTECT)
    borrower = models.ForeignKey('target_core.Borrower', on_delete=models.PROTECT, related_name='work_orders')
    number = models.CharField(max_length=100, blank=True, db_index=True)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    # WorkOrderStatusEnum. The legacy line setting it is commented out, so 11,998
    # of 12,285 imported orders carry none; it drives no behaviour.
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_number_old = models.CharField(max_length=45, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)
    # Set only on orders created by this system.
    request_key = models.UUIDField(null=True, unique=True, editable=False)
    request_hash = models.CharField(max_length=64, blank=True, editable=False)
    local_sequence = models.PositiveBigIntegerField(null=True, unique=True, editable=False)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT,
                                  related_name='work_orders_issued')
    issued_at = models.DateTimeField(null=True)

    class Meta:
        app_label = "target_core"
        constraints = [
            # One work order per borrower going forward. Four legacy borrowers
            # hold two, apparently from double submission; they are preserved.
            models.UniqueConstraint(fields=['borrower'], condition=Q(local_sequence__isnull=False),
                                    name='one_new_work_order_per_borrower'),
            # Numbers unique among orders this system allocates.
            models.UniqueConstraint(fields=['number'], condition=Q(local_sequence__isnull=False),
                                    name='unique_new_work_order_number'),
        ]


class WorkOrderRevision(Entity):
    lead = models.ForeignKey('target_core.Lead', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['WorkOrder', 'WorkOrderRevision']
