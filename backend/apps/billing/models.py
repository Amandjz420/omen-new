"""billing model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Invoice(Entity):
    valuation = models.ForeignKey('target_core.Valuation', null=True, on_delete=models.PROTECT)
    office = models.ForeignKey('target_core.ClientOffice', null=True, on_delete=models.PROTECT)
    number = models.CharField(max_length=100, blank=True, db_index=True)
    origin = models.CharField(max_length=30)  # online/offline remain distinguishable
    issued_date = models.DateField(null=True)
    due_date = models.DateField(null=True)
    currency = models.CharField(max_length=3, blank=True)
    billed_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_paid_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_remaining_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
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
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['number'], condition=Q(local_sequence__isnull=False),
                                               name='unique_new_invoice_number')]


class InvoiceLine(Entity):
    """A charge as it stood when the invoice was issued. A tax invoice must not
    change after issue, so the lines are a snapshot rather than a view of the
    valuation's current billing."""
    invoice = models.ForeignKey('target_core.Invoice', on_delete=models.PROTECT, related_name='lines')
    description = models.TextField()
    net_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    tax_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    charge_type = models.ForeignKey('ChargeType', null=True, blank=True, on_delete=models.PROTECT)
    cgst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    sgst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    igst = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "target_core"


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
    invoice = models.ForeignKey('target_core.Invoice', null=True, on_delete=models.PROTECT, related_name='receipts')
    valuation = models.ForeignKey('Valuation', null=True, on_delete=models.PROTECT)
    office = models.ForeignKey('target_core.ClientOffice', null=True, on_delete=models.PROTECT)
    borrower = models.ForeignKey('target_core.Borrower', null=True, on_delete=models.PROTECT)
    document = models.ForeignKey('target_core.Document', null=True, on_delete=models.PROTECT)
    payer_name = models.CharField(max_length=300, blank=True)
    mode = models.CharField(max_length=40, blank=True)
    remark = models.TextField(blank=True)
    # Cash receipt detail (legacy cash_receipt).
    RECEIVED_AS = [(1, 'Advance'), (2, 'Recovery'), (3, 'Other')]                    # CashRecieptRecievedEnum
    received_as = models.IntegerField(null=True, blank=True, choices=RECEIVED_AS)
    MODES = [(1, 'Cash'), (2, 'Cheque'), (3, 'Draft'), (4, 'Netbanking'), (5, 'UPI')]  # CaseReceiptPaymentModeEnum
    payment_mode = models.IntegerField(null=True, blank=True, choices=MODES)
    mobile = models.CharField(max_length=500, blank=True)
    amount_received_on = models.DateField(null=True, blank=True)
    cheque_draft_number = models.CharField(max_length=200, blank=True)
    cheque_draft_bank = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    in_favour_of = models.CharField(max_length=500, blank=True)
    proforma_invoice_number = models.CharField(max_length=500, blank=True)
    received_against_code = models.IntegerField(null=True, blank=True)
    receivable_bank_code = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=500, blank=True)
    # Maker, checker and verifier: three steps before a receipt counts.
    maker = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    checked_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    checked_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('LegacyAccount', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    verified_at = models.DateTimeField(null=True, blank=True)
    # The legacy amount_received table (2019-2022) was copied into cash_receipt when
    # cash receipts replaced it: 1,518 of its 1,519 entries match a cash receipt on
    # the same invoice, amount and date. The older copy is kept as evidence and
    # points at the receipt it duplicates, and is never counted towards a total.
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='duplicates')

    class Meta:
        app_label = "target_core"


class ReceiptAllocation(Entity):
    receipt = models.ForeignKey('target_core.Receipt', on_delete=models.PROTECT)
    invoice = models.ForeignKey('target_core.Invoice', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=24, decimal_places=6)
    posting_key = models.CharField(max_length=100, unique=True)
    class Meta:
        app_label = "target_core"
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name='allocation_amount_positive')]


class ChargeType(NamedEntity):
    # Legacy order follows billing_head_id; the discount head is legacy id 2.
    source_sequence = models.PositiveIntegerField(null=True, db_index=True)
    charge_kind = models.CharField(max_length=40, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ValuationCharge(Entity):
    valuation = models.ForeignKey('Valuation', on_delete=models.PROTECT, related_name='charges')
    charge_type = models.ForeignKey('target_core.ChargeType', null=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    cgst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    sgst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    igst = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    total_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)

    class Meta:
        app_label = "target_core"


class InvoiceFollowUp(Entity):
    invoice = models.ForeignKey('target_core.Invoice', null=True, on_delete=models.PROTECT, related_name='follow_ups')
    call_status = models.CharField(max_length=50, blank=True)
    logged_date_text = models.CharField(max_length=50, blank=True)
    logged_time_text = models.CharField(max_length=20, blank=True)
    remark = models.TextField(blank=True)
    legacy_update_date = models.CharField(max_length=45, blank=True)

    class Meta:
        app_label = "target_core"


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

    class Meta:
        app_label = "target_core"


class FeeRule(Entity):
    bank = models.ForeignKey('target_core.Bank', null=True, on_delete=models.PROTECT)
    fmv_category = models.CharField(max_length=40, blank=True)
    fmv_range_min = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    fmv_range_max = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    per_lac_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    additional_charge = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    min_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    max_fee = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class CreditNote(Entity):
    """Reverses an issued invoice in full. The legacy system had no way to
    reverse an invoice: 21 valuations were cancelled with their invoice left
    standing. An issued invoice is never edited or deleted; it is credited."""
    invoice = models.ForeignKey('target_core.Invoice', on_delete=models.PROTECT, related_name='credit_notes')
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
    document = models.ForeignKey('target_core.Document', null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        app_label = "target_core"


__all__ = ['ChargeType', 'ValuationCharge', 'Invoice', 'InvoiceLine', 'Receipt', 'ReceiptAllocation', 'InvoiceFollowUp', 'IssuerAccount', 'FeeRule', 'CreditNote']
