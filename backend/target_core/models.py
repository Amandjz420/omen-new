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
    # The account this employee signs in with, if any. An employee may have no
    # login and still hold historical assignments; an account may exist with no
    # employee. Set only by provisioning, never by the data importer.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.PROTECT, related_name='employee_profile')


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
    gstin = models.CharField(max_length=200, blank=True)          # printed on invoices billed to the client
    ifsc = models.CharField(max_length=45, blank=True)


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
    intake_key = models.UUIDField(null=True, unique=True, editable=False)
    intake_hash = models.CharField(max_length=64, blank=True, editable=False)
    local_sequence = models.PositiveBigIntegerField(null=True, unique=True, editable=False)
    number = models.CharField(max_length=100, blank=True, db_index=True)
    office = models.ForeignKey(ClientOffice, on_delete=models.PROTECT)
    contact = models.ForeignKey(Contact, null=True, on_delete=models.PROTECT)
    assigned_employee = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
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
    received_by = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT, related_name='leads_received')
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    legacy_number_old = models.CharField(max_length=45, blank=True)


class RequestedService(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    party_count = models.PositiveIntegerField(null=True)
    case_count = models.PositiveIntegerField(null=True)


class LeadCounter(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    value = models.PositiveBigIntegerField(default=0)


class LocalRecord(Entity):
    """A reviewed local edit transfers this record's ownership from the importer."""
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['target_model', 'target_id'], name='local_record_unique')]


class IntakeAudit(Entity):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    target_model = models.CharField(max_length=100)
    target_id = models.UUIDField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)


class Borrower(NamedEntity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
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


class Case(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
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
    """A work order is issued per borrower, not per lead (legacy lead_order)."""
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='work_orders')
    number = models.CharField(max_length=100, blank=True, db_index=True)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
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
        constraints = [
            # One work order per borrower going forward. Four legacy borrowers
            # hold two, apparently from double submission; they are preserved.
            models.UniqueConstraint(fields=['borrower'], condition=Q(local_sequence__isnull=False),
                                    name='one_new_work_order_per_borrower'),
            # Numbers unique among orders this system allocates.
            models.UniqueConstraint(fields=['number'], condition=Q(local_sequence__isnull=False),
                                    name='unique_new_work_order_number'),
        ]


class Valuation(Entity):
    """One per case. legacy_status is the live status and holds the legacy text
    values: Pending, Submit, Hold, Cancel, Revert. ValuationStatusEnum gives Hold
    and Cancel the same number, but the source stores names, so nothing is lost.
    Final approval is recorded on ValuationVerification; a completed valuation
    stays Submit."""
    case = models.ForeignKey(Case, on_delete=models.PROTECT)
    work_order = models.ForeignKey(WorkOrder, null=True, on_delete=models.PROTECT)
    assessor = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
    valuation_date = models.DateField(null=True)
    legacy_status = models.CharField(max_length=80, blank=True)
    report_number = models.CharField(max_length=100, blank=True)
    assessor_name = models.CharField(max_length=200, blank=True)
    submitted_to = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT, related_name='valuations_received')
    liable_employee = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT, related_name='valuations_liable')
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
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    # The Omen account the invoice directs payment to. Legacy invoice.bank_id, which
    # joins account_detail.bank_id; first imported wrongly as a bank.
    issuer_account = models.ForeignKey('IssuerAccount', null=True, blank=True, on_delete=models.PROTECT)
    GSTIN_PARTIES = [(1, 'Client'), (2, 'Client Customer'), (3, 'Other')]          # GstEnum
    gstin_party = models.IntegerField(null=True, blank=True, choices=GSTIN_PARTIES)
    other_gstin = models.CharField(max_length=100, blank=True)
    PAYERS = [(1, 'By Client'), (2, 'By Client Customer')]                        # PaidByEnum
    payer = models.IntegerField(null=True, blank=True, choices=PAYERS)
    PAYMENT_TYPES = [(1, 'Fully Payment'), (2, 'Partial Payment')]                 # InvoicePaymentTypeEnum
    payment_type = models.IntegerField(null=True, blank=True, choices=PAYMENT_TYPES)
    payment_date = models.DateField(null=True, blank=True)
    bad_debt_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    bad_debt_remark = models.TextField(blank=True)
    excess_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    remaining_words = models.CharField(max_length=500, blank=True)
    legacy_number_old = models.CharField(max_length=45, blank=True)
    PLACES = [('intra', 'Intra State (CGST + SGST)'), ('inter', 'Inter State (IGST)')]
    place_of_supply = models.CharField(max_length=10, blank=True, choices=PLACES)
    # Set only on invoices this system issues.
    local_sequence = models.PositiveBigIntegerField(null=True, blank=True, unique=True, editable=False)
    issued_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    issued_by_name = models.CharField(max_length=200, blank=True)
    # A cancelled invoice is reversed by a credit note and stays on record.
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['number'], condition=Q(local_sequence__isnull=False),
                                               name='unique_new_invoice_number')]


class InvoiceLine(Entity):
    """A charge as it stood when the invoice was issued. A tax invoice must not
    change after issue, so the lines are a snapshot rather than a view of the
    valuation's current billing."""
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='lines')
    description = models.TextField()
    net_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    tax_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    charge_type = models.ForeignKey('ChargeType', null=True, blank=True, on_delete=models.PROTECT)
    cgst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    sgst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    igst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)


class Receipt(Entity):
    number = models.CharField(max_length=100, blank=True)
    origin = models.CharField(max_length=40)
    received_date = models.DateField(null=True)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    currency = models.CharField(max_length=3, blank=True)
    verified = models.BooleanField(default=False)
    legacy_status = models.CharField(max_length=40, blank=True)
    # Legacy receipts do carry a settlement reference: cash_receipt names an
    # invoice directly, amount_received names the valuation. Both are recorded
    # so billing reconciliation has something to work from. Neither is a
    # posted allocation; ReceiptAllocation remains the ledger.
    invoice = models.ForeignKey(Invoice, null=True, on_delete=models.PROTECT, related_name='receipts')
    valuation = models.ForeignKey('Valuation', null=True, on_delete=models.PROTECT)
    office = models.ForeignKey(ClientOffice, null=True, on_delete=models.PROTECT)
    borrower = models.ForeignKey(Borrower, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    payer_name = models.CharField(max_length=300, blank=True)
    mode = models.CharField(max_length=40, blank=True)
    remark = models.TextField(blank=True)


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


# ============================================================================
# Organization: the legacy administrative geography hierarchy.
# state > district > block > panchayat > village, with the parallel
# region > circle and city > location > sublocation ladders. Parents are
# nullable because legacy keys are stored as varchar and do not all resolve.
# ============================================================================

class State(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class District(NamedEntity):
    state = models.ForeignKey(State, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Region(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Circle(NamedEntity):
    region = models.ForeignKey(Region, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Block(NamedEntity):
    district = models.ForeignKey(District, null=True, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, null=True, on_delete=models.PROTECT)
    circle = models.ForeignKey(Circle, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    area_type = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Panchayat(NamedEntity):
    block = models.ForeignKey(Block, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Village(NamedEntity):
    # uam_user.village.PANCHAYAT_ID is a 4-character local code ('0117'), not a
    # key into panchayat.panchayat_id (an 8-digit composite). No row joins, so
    # the raw code is preserved and the relationship is left unasserted.
    panchayat = models.ForeignKey(Panchayat, null=True, on_delete=models.PROTECT)
    legacy_panchayat_code = models.CharField(max_length=10, blank=True, db_index=True)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    area_type = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class City(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class Location(NamedEntity):
    city = models.ForeignKey(City, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class SubLocation(NamedEntity):
    location = models.ForeignKey(Location, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class AdministrativeDivision(NamedEntity):
    """uam_user.division. Distinct from the lead-management division master."""
    circle = models.ForeignKey(Circle, null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class OfficialLocation(NamedEntity):
    city = models.ForeignKey(City, null=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, blank=True)
    code = models.CharField(max_length=10, blank=True)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class IfscArea(Entity):
    """lead_mngt.ifsc has no primary key; the IFSC string is its natural key."""
    ifsc = models.CharField(max_length=45, db_index=True)
    state = models.ForeignKey(State, null=True, on_delete=models.PROTECT)
    district = models.ForeignKey(District, null=True, on_delete=models.PROTECT)
    block = models.ForeignKey(Block, null=True, on_delete=models.PROTECT)


# ============================================================================
# Lead operations: territory masters, follow-up calls, targets and assignment.
# Legacy follow-up stores its date and time as free text; the raw strings are
# preserved rather than guessed into typed columns.
# ============================================================================

class LeadDivision(NamedEntity):
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class LeadSubdivision(NamedEntity):
    division = models.ForeignKey(LeadDivision, null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class FollowUp(Entity):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name='follow_ups')
    call_status = models.CharField(max_length=50, blank=True)
    logged_date_text = models.CharField(max_length=50, blank=True)
    logged_time_text = models.CharField(max_length=20, blank=True)
    remark = models.TextField(blank=True)
    legacy_update_date = models.CharField(max_length=45, blank=True)


class EmployeeTarget(Entity):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    financial_year = models.CharField(max_length=20, blank=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    target_cases = models.PositiveIntegerField(null=True)
    target_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class EmployeeAssignmentRule(Entity):
    employee = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT)
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    asset_value = models.DecimalField(max_digits=24, decimal_places=6, null=True)


class LeadParty(Entity):
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT)
    borrower_name = models.CharField(max_length=300, blank=True)
    contact_person_name = models.CharField(max_length=300, blank=True)
    contact_number = models.CharField(max_length=80, blank=True)


# ============================================================================
# Documents: attachments and upload configuration. Metadata only; the files
# themselves are not retrieved by this importer.
# ============================================================================

class ValuationAttachment(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='attachments')
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=500, blank=True)
    attachment_type = models.CharField(max_length=40, blank=True)


class ScrutinyRequirement(NamedEntity):
    service = models.ForeignKey(ServiceType, null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class UploadConfiguration(Entity):
    """uam_user.upload_sys: system upload definitions, not business documents."""
    document_number = models.CharField(max_length=250, blank=True)
    document_type = models.CharField(max_length=150, blank=True)
    storage_key = models.TextField(blank=True)
    public_path = models.TextField(blank=True)
    original_name = models.CharField(max_length=300, blank=True)
    size_text = models.CharField(max_length=20, blank=True)
    uploaded_by_name = models.CharField(max_length=150, blank=True)


class LeadAttachment(Entity):
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    attachment_type = models.CharField(max_length=40, blank=True)
    remark = models.TextField(blank=True)
    proposal_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class DocumentUsage(Entity):
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    remarks = models.TextField(blank=True)


# ============================================================================
# Billing: charge heads, per-valuation charge lines, follow-up and the
# issuing account. Offline invoices and receipts import into Invoice/Receipt
# and stay distinguishable through their origin field.
# ============================================================================

class ChargeType(NamedEntity):
    # Legacy order follows billing_head_id; the discount head is legacy id 2.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    charge_kind = models.CharField(max_length=40, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class ValuationCharge(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='charges')
    charge_type = models.ForeignKey(ChargeType, null=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    cgst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    sgst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    igst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    total_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    # Totals are preserved as recorded; they are not recomputed from components.


class InvoiceFollowUp(Entity):
    invoice = models.ForeignKey(Invoice, null=True, on_delete=models.PROTECT, related_name='follow_ups')
    call_status = models.CharField(max_length=50, blank=True)
    logged_date_text = models.CharField(max_length=50, blank=True)
    logged_time_text = models.CharField(max_length=20, blank=True)
    remark = models.TextField(blank=True)
    legacy_update_date = models.CharField(max_length=45, blank=True)


class IssuerAccount(NamedEntity):
    """One of Omen's own bank accounts, printed on an invoice for payment.

    The legacy account_detail.bank_id is not a bank: it is the account's own code,
    1 to 4, which invoice.bank_id refers to. It was first imported as a link to the
    bank table, which attached each account to an unrelated bank (the Canara
    account to a co-operative bank). The account's bank is identified by its IFSC
    and name, which are what the invoice prints."""
    code = models.PositiveIntegerField(null=True, db_index=True)
    branch_code = models.CharField(max_length=40, blank=True)
    account_number = models.CharField(max_length=40, blank=True)
    ifsc_code = models.CharField(max_length=100, blank=True)
    branch_address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=100, blank=True)


# ============================================================================
# Valuations: the report form itself.
#
# The legacy form is entity-attribute-value and is preserved in that shape
# rather than pivoted, because the question set varies by service and changes
# over time. Question defines the attribute, QuestionOption its permitted
# values, and ValuationAnswer one stored cell.
#
# answer_type governs how a question renders and therefore how its answers are
# grouped (confirmed against the legacy JSP renderers):
#   1, 2  option list; one answer row per option
#   3     free text; a single answer row
#   4, 6  repeating grid; answer_group is the row index, options are columns
#   5     attribute/value table whose numeric values are totalled
# answer_group is therefore significant and is never collapsed.
#
# No uniqueness is asserted over (valuation, question, answer_group, option):
# the legacy data contains rows that repeat even that combination.
# ============================================================================

class QuestionCategory(NamedEntity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class Question(Entity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    service = models.ForeignKey(ServiceType, null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    category = models.ForeignKey(QuestionCategory, null=True, on_delete=models.PROTECT)
    text = models.TextField(blank=True)
    answer_type = models.PositiveSmallIntegerField(null=True)
    question_type = models.PositiveSmallIntegerField(null=True)
    is_document = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)
    display_order = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class QuestionOption(Entity):
    # Legacy ordering follows the source id; for options it fixes grid column order.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name='options')
    value = models.TextField(blank=True)
    value_type = models.CharField(max_length=200, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class ValuationAnswer(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    option = models.ForeignKey(QuestionOption, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    answer_group = models.PositiveIntegerField(default=0, db_index=True)
    value = models.TextField(blank=True)
    class Meta:
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


# ============================================================================
# Work orders: revisions and the fee rule table.
# ============================================================================

class WorkOrderRevision(Entity):
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)


class FeeRule(Entity):
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    fmv_category = models.CharField(max_length=40, blank=True)
    fmv_range_min = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    fmv_range_max = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    per_lac_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    additional_charge = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    min_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    max_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class ReportUsage(NamedEntity):
    """lead_mngt.usage_of_reports: why a valuation report was commissioned
    ("To give fresh loan"), scoped by service and subtype. Several tables store
    this id as a bare code; those codes are meaningless without this lookup."""
    service = models.ForeignKey(ServiceType, null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class BankReport(Entity):
    """lead_mngt.valuation_bank_report: the assessed values a valuation produces.

    This is valuation substance, not report formatting, despite the source
    catalogue filing it under reports. Amount words and the certificate text are
    retained as recorded; no amount is recomputed or derived from another.
    """
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='bank_reports')
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    branch = models.ForeignKey(BankBranch, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)
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


# ============================================================================
# Identity.
#
# The legacy UAM is a shared sign-on server for PRAYAS, PAYROLL and LEAD, so its
# records are frozen here as evidence rather than treated as the new system's
# account store. Django's User remains the authentication identity; these models
# hold what the legacy system knew and how it was translated.
#
# Geographic scope (region, circle, division, subdivision) is recorded exactly as
# found but is NOT an access restriction: by decision, no user is limited by
# region or circle. The values are kept so the choice can be revisited without
# re-deriving them.
# ============================================================================

class LegacyProject(NamedEntity):
    """uam_user.project: the applications sharing the legacy sign-on server."""
    legacy_status = models.CharField(max_length=40, blank=True)


class RoleDefinition(NamedEntity):
    """uam_user.usertype. A legacy job title, preserved for audit. Mapping these
    onto the new business roles is a separate reviewed decision."""
    project = models.ForeignKey(LegacyProject, null=True, on_delete=models.PROTECT)
    code = models.CharField(max_length=20, blank=True)
    name_hindi = models.CharField(max_length=500, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class LegacyAccount(NamedEntity):
    """uam_user.userdetail. Credentials are deliberately not imported: the legacy
    representation is not a Django-compatible hash and sits beside an
    old_password column suggesting reversible storage."""
    login_id = models.CharField(max_length=50, blank=True, db_index=True)
    email = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=12, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    # The legacy application treats userdetail.user_id and employee.emp_id as the
    # same number. That holds for 49 of 51 accounts, and on all 49 the names agree
    # as well, so the link is recorded where it resolves and left unset otherwise.
    employee = models.ForeignKey(Employee, null=True, on_delete=models.PROTECT, related_name='legacy_accounts')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.PROTECT, related_name='legacy_account')
    # Set when two legacy accounts are the same person. The duplicate keeps its
    # own record and its role grants, but provisions no second Django account.
    merged_into = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
                                    related_name='merged_accounts')
    merge_reason = models.CharField(max_length=300, blank=True)
    must_change_password = models.BooleanField(default=True)
    # The hash of the password this account was issued. Onboarding is complete
    # once the stored hash differs, whoever changed it and wherever from.
    issued_password_hash = models.CharField(max_length=128, blank=True, editable=False)
    provisioned_at = models.DateTimeField(null=True, blank=True)


class RoleAssignment(Entity):
    """uam_user.userdetail_per: which role a legacy account held, in which project."""
    account = models.ForeignKey(LegacyAccount, on_delete=models.PROTECT, related_name='role_assignments')
    role = models.ForeignKey(RoleDefinition, null=True, on_delete=models.PROTECT)
    project = models.ForeignKey(LegacyProject, null=True, on_delete=models.PROTECT)
    legacy_role_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)
    remark = models.CharField(max_length=250, blank=True)
    # Recorded, never enforced. See the module note above.
    scope_region = models.CharField(max_length=10, blank=True)
    scope_circle = models.CharField(max_length=10, blank=True)
    scope_division = models.CharField(max_length=10, blank=True)
    scope_subdivision = models.CharField(max_length=10, blank=True)


class LoginEvent(Entity):
    """uam_user.login_history. Historical evidence only; never a live session."""
    account = models.ForeignKey(LegacyAccount, null=True, on_delete=models.PROTECT, related_name='login_events')
    # Source columns are datetimes. Every retained login timestamp and almost
    # every logout timestamp has a non-midnight time, so dates cannot represent
    # session ordering or duration.
    login_at = models.DateTimeField(null=True, db_index=True)
    logout_at = models.DateTimeField(null=True)
    ip_address = models.CharField(max_length=100, blank=True)
    mac_address = models.CharField(max_length=100, blank=True)
    login_action = models.CharField(max_length=200, blank=True)


# ============================================================================
# Bank report templates.
#
# report_setup chooses a template for a (client type, service, subtype, bank)
# combination; report_question lays questions of the valuation form onto it
# under bank_report_heading sections, with the surrounding output text. Together
# they turn stored answers into the report a bank receives. Templates are
# configuration: a missing lookup is recorded rather than discarding the row,
# because a lost template line silently changes every report built from it.
# ============================================================================

class ReportTemplate(Entity):
    """lead_mngt.report_setup."""
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    service = models.ForeignKey(ServiceType, null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey(ServiceSubtype, null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class ReportHeading(NamedEntity):
    """lead_mngt.bank_report_heading: a section heading within a bank report."""
    client_type = models.ForeignKey(ClientType, null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    display_order = models.IntegerField(null=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class ReportTemplateLine(Entity):
    """lead_mngt.report_question: one question placed onto a template."""
    template = models.ForeignKey(ReportTemplate, on_delete=models.PROTECT, related_name='lines')
    question = models.ForeignKey(Question, null=True, on_delete=models.PROTECT)
    heading = models.ForeignKey(ReportHeading, null=True, on_delete=models.PROTECT)
    output_label = models.CharField(max_length=1000, blank=True)
    content_before = models.CharField(max_length=500, blank=True)
    content_after = models.CharField(max_length=500, blank=True)
    sequence = models.IntegerField(null=True)
    indexing = models.CharField(max_length=10, blank=True)


# ============================================================================
# Dispatch: physical and electronic delivery of reports and other documents.
#
# The legacy dispatch row holds no foreign key. The reports it carried are listed
# as comma-separated report numbers in nature_of_docs (the column name notwith-
# standing), which the legacy controller splits and joins to valuation.report_no.
# The raw list is preserved verbatim; DispatchItem records each reference and how
# it resolved. Codes are decoded from the legacy enums named beside each choice.
# ============================================================================

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


class DispatchItem(Entity):
    """One report reference within a dispatch, with its resolution recorded."""
    EXACT, NORMALIZED, LEAD_NUMBER, UNRESOLVED = 'exact', 'normalized', 'lead_number', 'unresolved'
    RESOLUTIONS = [(EXACT, 'Matched a report number exactly'),
                   (NORMALIZED, 'Matched after correcting spacing, hyphen or prefix'),
                   (LEAD_NUMBER, 'A lead number entered where a report number belongs'),
                   (UNRESOLVED, 'No valuation carries this report number')]

    dispatch = models.ForeignKey(Dispatch, on_delete=models.PROTECT, related_name='items')
    position = models.PositiveIntegerField()
    reference = models.CharField(max_length=100)
    valuation = models.ForeignKey('Valuation', null=True, on_delete=models.PROTECT, related_name='dispatch_items')
    lead = models.ForeignKey(Lead, null=True, on_delete=models.PROTECT)
    resolution = models.CharField(max_length=20, choices=RESOLUTIONS)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['dispatch', 'position'], name='dispatch_item_position')]


# ============================================================================
# SMS: customer notifications. The dispatch controller sends one on dispatch and
# one on delivery. The log runs from August 2023 to August 2024 and then stops,
# so messaging was live for about a year. IS_OTP is null on every row and the
# bodies are consent and delivery notices, not one-time codes.
# ============================================================================

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


class CreditNote(Entity):
    """Reverses an issued invoice in full. The legacy system had no way to
    reverse an invoice: 21 valuations were cancelled with their invoice left
    standing. An issued invoice is never edited or deleted; it is credited."""
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='credit_notes')
    number = models.CharField(max_length=100, db_index=True)
    local_sequence = models.PositiveBigIntegerField(unique=True, editable=False)
    issued_on = models.DateField()
    taxable_amount = models.DecimalField(max_digits=24, decimal_places=6)
    tax_amount = models.DecimalField(max_digits=24, decimal_places=6)
    total_amount = models.DecimalField(max_digits=24, decimal_places=6)
    reason = models.TextField()
    refund_due = models.DecimalField(max_digits=24, decimal_places=6, default=0)
    issued_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    issued_by_name = models.CharField(max_length=200, blank=True)
    document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.PROTECT)
