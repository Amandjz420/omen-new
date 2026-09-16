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
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
    document = models.ForeignKey(Document, null=True, on_delete=models.PROTECT)


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
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    remarks = models.TextField(blank=True)


# ============================================================================
# Billing: charge heads, per-valuation charge lines, follow-up and the
# issuing account. Offline invoices and receipts import into Invoice/Receipt
# and stay distinguishable through their origin field.
# ============================================================================

class ChargeType(NamedEntity):
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
    bank = models.ForeignKey(Bank, null=True, on_delete=models.PROTECT)
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
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)


class Question(Entity):
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


class Reversion(Entity):
    """A valuation sent back for correction."""
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='reversions')
    remark = models.CharField(max_length=300, blank=True)
    reverted_on = models.DateField(null=True)
    reverted_by_name = models.CharField(max_length=200, blank=True)


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
