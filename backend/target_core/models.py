"""Managed target entities. Source data is imported only after mapping validation.

No attendance-history tables are created. Source identity lives in a separate
ledger, so table consolidation cannot accidentally collapse equal legacy IDs.
"""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class ImportBatch(Entity):
    snapshot_checksum = models.CharField(max_length=64)
    conversion_version = models.CharField(max_length=80)
    source_environment = models.CharField(max_length=20)
    status = models.CharField(max_length=30, default='staged')
    summary = models.JSONField(default=dict)


class SourceIdentity(Entity):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)
    environment = models.CharField(max_length=20)
    schema = models.CharField(max_length=80)
    table = models.CharField(max_length=100)
    # Canonical typed JSON for key components, not a concatenation of bare values.
    key = models.CharField(max_length=512)
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=['environment','schema','table','key'], name='source_identity_unique')]


class MigrationIssue(Entity):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)
    source_identity = models.JSONField(default=dict)
    reason = models.TextField()
    resolution = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)


class NamedEntity(Entity):
    name = models.CharField(max_length=500)
    class Meta:
        abstract = True


class Bank(NamedEntity):
    legacy_status = models.CharField(max_length=40, blank=True)


class BankBranch(NamedEntity):
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    ifsc = models.CharField(max_length=40, blank=True, db_index=True)
    micr = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=150, blank=True)
    district = models.CharField(max_length=150, blank=True)
    state = models.CharField(max_length=150, blank=True)
    # IFSC is searchable, not assumed globally unique across historical versions.


class ClientType(NamedEntity):
    pass


class Employee(NamedEntity):
    employee_code = models.CharField(max_length=100, blank=True, db_index=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    # HR identity only. Login provisioning is a separate reviewed process.


class ClientOffice(NamedEntity):
    branch_name = models.CharField(max_length=500, blank=True)
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    directory_branch = models.ForeignKey(BankBranch, null=True, on_delete=models.PROTECT)
    address = models.TextField(blank=True)
    owner = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
    legacy_working_status = models.CharField(max_length=40, blank=True)
    state = models.CharField(max_length=150, blank=True)
    district = models.CharField(max_length=150, blank=True)


class ContactDesignation(NamedEntity):
    pass


class Contact(NamedEntity):
    office = models.ForeignKey(ClientOffice, on_delete=models.PROTECT)
    designation = models.ForeignKey(ContactDesignation, null=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=80, blank=True)
    alternate_phone = models.CharField(max_length=80, blank=True)
    # No global phone uniqueness: shared numbers and posting changes are possible.


class ServiceType(NamedEntity):
    pass


class ServiceSubtype(NamedEntity):
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)


class Lead(Entity):
    number = models.CharField(max_length=100, blank=True, db_index=True)
    office = models.ForeignKey(ClientOffice, on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, null=True, on_delete=models.PROTECT)
    assigned_employee = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
    received_date = models.DateField(null=True, db_index=True)
    date_basis = models.CharField(max_length=40, default='unknown')
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class RequestedService(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    party_count = models.PositiveIntegerField(null=True)
    case_count = models.PositiveIntegerField(null=True)


class Borrower(NamedEntity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    agreed_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    currency = models.CharField(max_length=3, blank=True)
    property_count = models.PositiveIntegerField(null=True)


class Case(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    asset_address = models.TextField(blank=True)
    asset_district = models.CharField(max_length=150, blank=True)
    asset_state = models.CharField(max_length=150, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Document(Entity):
    storage_provider = models.CharField(max_length=40)
    storage_container = models.CharField(max_length=300, blank=True)
    storage_key = models.TextField()
    original_name = models.TextField(blank=True)
    media_type = models.CharField(max_length=150, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True)
    checksum = models.CharField(max_length=64, blank=True)
    content_verified = models.BooleanField(default=False)


class WorkOrder(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, blank=True, db_index=True)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)


class Valuation(Entity):
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    work_order = models.ForeignKey(WorkOrder, null=True, on_delete=models.PROTECT)
    assessor = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
    valuation_date = models.DateField(null=True)
    legacy_status = models.CharField(max_length=80, blank=True)
    report_number = models.CharField(max_length=100, blank=True)


class Invoice(Entity):
    valuation = models.ForeignKey(Valuation, null=True, on_delete=models.PROTECT)
    office = models.ForeignKey(ClientOffice, null=True, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, blank=True, db_index=True)
    origin = models.CharField(max_length=30)  # online/offline remain distinguishable
    issued_date = models.DateField(null=True)
    due_date = models.DateField(null=True)
    currency = models.CharField(max_length=3, blank=True)
    billed_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_paid_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_remaining_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class InvoiceLine(Entity):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    description = models.TextField()
    net_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    tax_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)


class Receipt(Entity):
    number = models.CharField(max_length=100, blank=True)
    origin = models.CharField(max_length=40)
    received_date = models.DateField(null=True)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    currency = models.CharField(max_length=3, blank=True)
    verified = models.BooleanField(default=False)
    legacy_status = models.CharField(max_length=40, blank=True)


class ReceiptAllocation(Entity):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=24, decimal_places=6)
    posting_key = models.CharField(max_length=100, unique=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='allocation_amount_positive')]
    # A transaction service must enforce cumulative allocation and currency agreement.


class SalaryBaseline(Entity):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    source_variant = models.CharField(max_length=80)


class SalaryBaselineComponent(Entity):
    baseline = models.ForeignKey(SalaryBaseline, on_delete=models.PROTECT)
    pay_code = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    from_period = models.CharField(max_length=20, blank=True)
    to_period = models.CharField(max_length=20, blank=True)
    mode = models.CharField(max_length=40, blank=True)


class SalaryResult(Entity):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    period = models.CharField(max_length=20)
    gross_earning = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    gross_deduction = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    net_salary = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    paid_days = models.DecimalField(max_digits=8, decimal_places=3, null=True)
    legacy_payment_status = models.CharField(max_length=80, blank=True)
    # Preserve issued results; do not recompute them from an empty attendance module.


class LeaveOpeningBalance(Entity):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    leave_type_code = models.CharField(max_length=80)
    as_of_date = models.DateField()
    days = models.DecimalField(max_digits=10, decimal_places=3)
    evidence = models.JSONField(default=dict)
    reconciled = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['employee','leave_type_code','as_of_date'], name='leave_opening_balance_unique')]


class SourceRow(Entity):
    """Latest source row for replay/quarantine, not a competing business model."""
    schema = models.CharField(max_length=80)
    table = models.CharField(max_length=100)
    key = models.CharField(max_length=512)
    payload = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64)
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT)
    outcome = models.CharField(max_length=30)
    problems = models.JSONField(default=list)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['schema','table','key'],name='source_row_unique')]


class LeadNote(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=4000)
    prototype_note_id = models.BigIntegerField(null=True, unique=True)
