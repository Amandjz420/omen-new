"""The MIS: the previous system's management reports, counted correctly.

Traced to report/report_home.jsp and MonthWiseLeadReportController,
RecoveryReportStatus, InvoiceService and LeadStatusCountService in omen-lead-new;
the legacy queries and the defects found by running them are recorded in
migration-required/data-migration/MIS_LEGACY_QUERIES.md. Per the data owner, the
reports show only correct figures.

One engine serves every report. A report names its records, the date they are
filtered by, the groupings it offers, what it totals, and the columns of its detail
list. The engine applies the filters, groups, totals, lists the records behind a
group, and exports to Excel.

Money is counted once per invoice, from the invoice itself. The legacy invoice and
recovery reports joined each invoice to its charge lines, six rows per invoice,
and summed across them, so totals came out six times too high (money still owed:
Rs 67.7 lakh reported, Rs 11.3 lakh true). Every standing invoice is counted,
including the 43 the legacy inner joins left out; an invoice reversed by a credit
note is not.

The eleven legacy invoice and recovery reports (3.1-3.6 and 4.1-4.6) were one
query with different filter forms; here they are two reports, Invoices and
Outstanding, each with the six groupings. 3.6 linked to 3.5's address; both
groupings exist here. Offline invoices are reported separately, as the legacy
system did.

Pending recovery (3.7) buckets outstanding invoices by age. The legacy bands,
0-60, 60-90, 90-120 and over 120 days, used BETWEEN, so an invoice exactly 60 or 90
days old fell into two bands; here each invoice falls into exactly one.

A user restricted to their own leads sees only their own figures.
"""
import datetime
from collections import OrderedDict
from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from target_core import models as m
from apps.common.http import IntakeError, endpoint
from apps.migration_pipeline.services import source_key
from apps.valuations.services import scope_cases, scope_leads, scoped_employee

ZERO = Decimal('0')
PAGE_SIZE = 50


def money(v):
    return (v or ZERO).quantize(Decimal('0.01'))


# --- the records each report reads -------------------------------------------

INVOICE_FIELDS = dict(
    id='pk', invoice='number', issued='issued_date', billed='billed_amount', paid='legacy_paid_amount',
    outstanding='legacy_remaining_amount', written_off='bad_debt_amount', excess='excess_amount',
    report='valuation__report_number', status='valuation__legacy_status', lead='valuation__case__lead__number',
    borrower='valuation__case__borrower__name', office='valuation__case__lead__office__name',
    branch='valuation__case__lead__office__branch_name', office_id='valuation__case__lead__office_id',
    service='valuation__case__service__name', service_id='valuation__case__service_id',
    subtype='valuation__case__subtype__name', district='valuation__case__asset_district', state='valuation__case__asset_state',
    assessor='valuation__case__lead__assigned_employee__name', assessor_id='valuation__case__lead__assigned_employee_id',
    division='valuation__case__lead__contact__division__name', division_id='valuation__case__lead__contact__division_id',
)


def invoices(user, f, outstanding=False):
    """Standing invoices on valuations, dated by invoice date. Offline invoices, which
    belong to no valuation, are reported separately."""
    qs = m.Invoice.objects.filter(cancelled_at__isnull=True, valuation__isnull=False)
    if scoped_employee(user) is not None:
        qs = qs.filter(valuation__case__in=scope_cases(user, m.Case.objects.all()))
    if outstanding:
        # As the legacy recovery reports: money still owed, on work not cancelled.
        qs = qs.filter(legacy_remaining_amount__gt=0).exclude(valuation__legacy_status='Cancel')
    qs = common_filters(qs, f, date='issued_date', prefix='valuation__case__')
    rows = []
    for r in qs.values(*INVOICE_FIELDS.values()):
        row = {k: r[v] for k, v in INVOICE_FIELDS.items()}
        for k in ('billed', 'paid', 'outstanding', 'written_off', 'excess'):
            row[k] = max(money(row[k]), ZERO) if k == 'outstanding' else money(row[k])
        rows.append(row)
    return rows


def common_filters(qs, f, date, prefix):
    if f['from']:
        qs = qs.filter(**{f'{date}__gte': f['from']})
    if f['to']:
        qs = qs.filter(**{f'{date}__lte': f['to']})
    if f['office']:
        qs = qs.filter(**{f'{prefix}lead__office_id': f['office']})
    if f['service']:
        qs = qs.filter(**{f'{prefix}service_id': f['service']})
    if f['assessor']:
        qs = qs.filter(**{f'{prefix}lead__assigned_employee_id': f['assessor']})
    if f['division']:
        qs = qs.filter(**{f'{prefix}lead__contact__division_id': f['division']})
    if f['district']:
        qs = qs.filter(**{f'{prefix}asset_district__iexact': f['district']})
    if f['q']:
        q = f['q']
        qs = qs.filter(Q(**{f'{prefix}lead__number__icontains': q}) | Q(**{f'{prefix}borrower__name__icontains': q})
                       | Q(**{f'{prefix}lead__office__name__icontains': q}))
    return qs


def age_band(issued, today):
    days = (today - issued).days if issued else None
    if days is None:
        return ('9', 'Date unknown')
    if days <= 60:
        return ('1', '0 to 60 days')
    if days <= 90:
        return ('2', '61 to 90 days')
    if days <= 120:
        return ('3', '91 to 120 days')
    return ('4', 'Over 120 days')


def liable_assessors():
    """Legacy bank reports store the liable field assessor as a legacy employee id;
    resolve each to the employee through the import's identity records."""
    by_key = dict(m.SourceIdentity.objects.filter(environment='main', schema='uam_user', table='employee')
                  .values_list('key', 'target_id'))
    names = dict(m.Employee.objects.values_list('id', 'name'))
    return lambda code: (lambda t: (str(t), names.get(t, 'Unknown')) if t else None)(by_key.get(source_key(code)) if code else None)


def bank_reports(user, f):
    """Current bank reports with a liable field assessor, and the invoice on the same
    valuation. As the legacy report, the date filter applies to the invoice date."""
    qs = m.BankReport.objects.filter(superseded_at__isnull=True)
    if scoped_employee(user) is not None:
        qs = qs.filter(valuation__case__in=scope_cases(user, m.Case.objects.all()))
    qs = common_filters(qs, {**f, 'from': None, 'to': None}, date='report_date', prefix='valuation__case__')
    resolve = liable_assessors()
    standing = {i['valuation_id']: i for i in m.Invoice.objects.filter(cancelled_at__isnull=True, valuation__isnull=False)
                .values('valuation_id', 'number', 'issued_date', 'billed_amount')}
    rows = []
    for r in qs.values('pk', 'valuation_id', 'valuation__report_number', 'legacy_liable_fa', 'valuation__liable_employee_id',
                       'valuation__liable_employee__name', 'valuation__case__lead__office__name', 'valuation__case__borrower__name',
                       'liable_employee_id', 'liable_employee__name'):
        # The bank report names who is liable, and it is the document of record: the
        # one the bank received. The valuation's own field is the fallback, for
        # reports generated here, which do not store one. Where the two disagree the
        # legacy reports followed the bank report.
        # A report generated or corrected here names its assessor directly; it had none,
        # so the report skipped every invoice issued in the new system.
        fa = ((str(r['liable_employee_id']), r['liable_employee__name']) if r['liable_employee_id'] else None) \
            or resolve(r['legacy_liable_fa']) or ((str(r['valuation__liable_employee_id']), r['valuation__liable_employee__name'])
                                                  if r['valuation__liable_employee_id'] else None)
        if fa is None:
            continue
        inv = standing.get(r['valuation_id'])
        if (f['from'] or f['to']) and not (inv and inv['issued_date'] and (not f['from'] or inv['issued_date'] >= f['from'])
                                           and (not f['to'] or inv['issued_date'] <= f['to'])):
            continue
        rows.append({'id': r['pk'], 'report': r['valuation__report_number'], 'liable_id': fa[0], 'liable': fa[1],
                     'office': r['valuation__case__lead__office__name'], 'borrower': r['valuation__case__borrower__name'],
                     'invoice': inv['number'] if inv else '', 'issued': inv['issued_date'] if inv else None,
                     'billed': money(inv['billed_amount']) if inv else ZERO, 'reports': 1})
    return rows


LEAD_STATUS = {'1': 'New lead', '2': 'In process', '3': 'Cancelled', '4': 'Closed'}
VALUATION_STATUS = {'Pending': 'Being filled in', 'Submit': 'Submitted', 'Revert': 'Sent back', 'Hold': 'On hold', 'Cancel': 'Cancelled'}


def leads(user, f):
    """Leads, dated by the date they were received. Deleted leads are left out; the
    legacy lead queries had no such filter and counted them."""
    qs = m.Lead.objects.exclude(legacy_deleted='1')
    qs = scope_leads(user, qs)
    qs = common_filters(qs, f, date='received_date', prefix='')
    from django.db.models import Count
    qs = qs.annotate(borrower_count=Count('borrower', distinct=True, filter=~Q(borrower__legacy_deleted='1')))
    return [{'id': r['pk'], 'lead': r['number'], 'received': r['received_date'], 'status_code': r['legacy_status'],
             'status': LEAD_STATUS.get(r['legacy_status'], 'Other'), 'office': r['office__name'], 'branch': r['office__branch_name'],
             'office_id': r['office_id'], 'orderer': r['contact__name'], 'orderer_phone': r['contact__phone'],
             'assessor': r['assigned_employee__name'], 'assessor_id': r['assigned_employee_id'], 'borrowers': r['borrower_count'],
             'division': r['contact__division__name'], 'division_id': r['contact__division_id']}
            for r in qs.values('pk', 'number', 'received_date', 'legacy_status', 'office__name', 'office__branch_name', 'office_id',
                               'contact__name', 'contact__phone', 'assigned_employee__name', 'assigned_employee_id', 'borrower_count',
                               'contact__division__name', 'contact__division_id')]


def valuations(user, f, cancelled=False):
    """Valuations, dated by the valuation date; cancelled ones by the date they were
    cancelled. The legacy cancelled-valuations report grouped by client while
    listing valuations, so it showed one per client: 277 of 700."""
    qs = m.Valuation.objects.all()
    if cancelled:
        qs = qs.filter(legacy_status='Cancel')
    if scoped_employee(user) is not None:
        qs = qs.filter(case__in=scope_cases(user, m.Case.objects.all()))
    qs = common_filters(qs, f, date='status_reason_date' if cancelled else 'valuation_date', prefix='case__')
    return [{'id': r['pk'], 'report': r['report_number'], 'status_code': r['legacy_status'],
             'status': VALUATION_STATUS.get(r['legacy_status'], r['legacy_status'] or 'Not started'),
             'valued': r['valuation_date'], 'cancelled_on': r['status_reason_date'], 'reason': r['status_reason'],
             'lead': r['case__lead__number'], 'work_order': r['work_order__number'], 'borrower': r['case__borrower__name'],
             'office': r['case__lead__office__name'], 'branch': r['case__lead__office__branch_name'], 'office_id': r['case__lead__office_id'],
             'ifsc': r['case__lead__office__ifsc'], 'service': r['case__service__name'], 'service_id': r['case__service_id'],
             'subtype': r['case__subtype__name'], 'district': r['case__asset_district'], 'state': r['case__asset_state'],
             'doer': r['assessor__name'] or (r['assessor_name'] or '').strip(), 'doer_id': r['assessor_id'],
             'assessor': r['case__lead__assigned_employee__name'], 'assessor_id': r['case__lead__assigned_employee_id'],
             'division': r['case__lead__contact__division__name'], 'division_id': r['case__lead__contact__division_id']}
            for r in qs.values('pk', 'report_number', 'legacy_status', 'valuation_date', 'status_reason_date', 'status_reason',
                               'case__lead__number', 'work_order__number', 'case__borrower__name', 'case__lead__office__name',
                               'case__lead__office__branch_name', 'case__lead__office_id', 'case__lead__office__ifsc',
                               'case__service__name', 'case__service_id', 'case__subtype__name', 'case__asset_district',
                               'case__asset_state', 'assessor__name', 'assessor_name', 'assessor_id',
                               'case__lead__assigned_employee__name', 'case__lead__assigned_employee_id',
                               'case__lead__contact__division__name', 'case__lead__contact__division_id')]


def month(field):
    return lambda r: (r[field].strftime('%Y-%m') if r.get(field) else '', r[field].strftime('%B %Y') if r.get(field) else 'Date unknown')


def status_of(labels):
    order = {k: str(i) for i, k in enumerate(labels)}
    return lambda r: (order.get(r['status_code'], '9'), r['status'])


# --- the reports -------------------------------------------------------------

def by(field, label_field=None, blank='Not recorded'):
    return lambda r: (str(r.get(field) or ''), (r.get(label_field or field) or blank))


INVOICE_GROUPS = OrderedDict([
    ('area', ('Area', lambda r: ((r['district'] or '').lower(), ', '.join(x for x in (r['district'], r['state']) if x) or 'Area not recorded'))),
    ('assessor', ('Field assessor', by('assessor_id', 'assessor', 'Not assigned'))),
    ('customer', ('Client customer', lambda r: ((r['borrower'] or '').strip().lower(), (r['borrower'] or '').strip() or 'Not recorded'))),
    ('client', ('Client', lambda r: (str(r['office_id']), ', '.join(x for x in (r['office'], r['branch']) if x) or 'Not recorded'))),
    ('service', ('Service rendered', by('service_id', 'service'))),
    ('division', ('Division', by('division_id', 'division', 'No division'))),
])
MONEY = [('invoices', 'Invoices', 'count'), ('billed', 'Invoiced', 'money'), ('paid', 'Received', 'money'),
         ('written_off', 'Written off', 'money'), ('outstanding', 'Outstanding', 'money')]
INVOICE_COLUMNS = [('invoice', 'Invoice', 'text'), ('issued', 'Date', 'date'), ('report', 'Report', 'text'), ('lead', 'Lead', 'text'),
                   ('office', 'Client', 'text'), ('borrower', 'Client customer', 'text'), ('service', 'Service', 'text'),
                   ('district', 'District', 'text'), ('assessor', 'Field assessor', 'text'),
                   ('billed', 'Invoiced', 'money'), ('paid', 'Received', 'money'), ('outstanding', 'Outstanding', 'money')]

REPORTS = OrderedDict()


def report(key, **spec):
    REPORTS[key] = {'key': key, **spec}


report('invoices', number='4', title='Invoices', section='Billing',
       description='Every standing invoice, with what was received and what is still owed, counted once per invoice.',
       date_label='Invoice date', rows=lambda u, f: invoices(u, f), groups=INVOICE_GROUPS, default_group='client',
       measures=MONEY, columns=INVOICE_COLUMNS)
report('outstanding', number='3', title='Outstanding', section='Recovery',
       description='Invoices with money still owed, on work that was not cancelled.',
       date_label='Invoice date', rows=lambda u, f: invoices(u, f, outstanding=True), groups=INVOICE_GROUPS, default_group='client',
       sort='outstanding', measures=MONEY, columns=INVOICE_COLUMNS)
report('pending-recovery', number='3.7', title='Pending recovery', section='Recovery',
       description='Money still owed, by how long it has been owed. Each invoice falls into exactly one band.',
       date_label='Invoice date', rows=lambda u, f: invoices(u, f, outstanding=True),
       groups=OrderedDict([('age', ('Days since invoice', lambda r: age_band(r['issued'], timezone.localdate()))), *INVOICE_GROUPS.items()]),
       default_group='age', sort='outstanding', measures=MONEY, columns=INVOICE_COLUMNS)
report('total-amount', number='(total)', title='Total amount', section='Billing',
       description='Invoiced, received and still owed, across all standing invoices.',
       date_label='Invoice date', rows=lambda u, f: invoices(u, f),
       groups=OrderedDict([('month', ('Month', lambda r: (r['issued'].strftime('%Y-%m') if r['issued'] else '', r['issued'].strftime('%B %Y') if r['issued'] else 'Date unknown'))),
                           ('all', ('All invoices', lambda r: ('all', 'All standing invoices')))]),
       default_group='all', measures=MONEY, columns=INVOICE_COLUMNS)
report('billing-by-client', number='8', title='Billing by client', section='Billing',
       description='What each client was invoiced.', date_label='Invoice date', rows=lambda u, f: invoices(u, f),
       groups=OrderedDict([('client', INVOICE_GROUPS['client'])]), default_group='client',
       measures=[('invoices', 'Invoices', 'count'), ('billed', 'Invoiced', 'money')], columns=INVOICE_COLUMNS)
report('billing-by-assessor', number='7', title='Billing by liable field assessor', section='Billing',
       description='Bank reports each liable field assessor is answerable for, and what their valuations were invoiced.',
       date_label='Invoice date', rows=bank_reports,
       groups=OrderedDict([('liable', ('Liable field assessor', by('liable_id', 'liable')))]), default_group='liable',
       measures=[('reports', 'Bank reports', 'count'), ('billed', 'Invoiced', 'money')],
       columns=[('report', 'Report', 'text'), ('office', 'Client', 'text'), ('borrower', 'Client customer', 'text'),
                ('invoice', 'Invoice', 'text'), ('issued', 'Invoice date', 'date'), ('billed', 'Invoiced', 'money')])


LEAD_GROUPS = OrderedDict([
    ('status', ('Lead status', status_of(LEAD_STATUS))),
    ('month', ('Month received', month('received'))),
    ('client', ('Client', lambda r: (str(r['office_id']), ', '.join(x for x in (r['office'], r['branch']) if x) or 'Not recorded'))),
    ('assessor', ('Field assessor', by('assessor_id', 'assessor', 'Not assigned'))),
    ('division', ('Division', by('division_id', 'division', 'No division'))),
])
LEAD_MEASURES = [('leads', 'Leads', 'count'), ('new', 'New', 'count', lambda r: r['status_code'] == '1'),
                 ('in_process', 'In process', 'count', lambda r: r['status_code'] == '2'),
                 ('cancelled', 'Cancelled', 'count', lambda r: r['status_code'] == '3'),
                 ('closed', 'Closed', 'count', lambda r: r['status_code'] == '4'), ('borrowers', 'Borrowers', 'number')]
LEAD_COLUMNS = [('lead', 'Lead', 'text'), ('received', 'Received', 'date'), ('status', 'Status', 'text'), ('office', 'Client', 'text'),
                ('orderer', 'Orderer', 'text'), ('orderer_phone', 'Orderer phone', 'text'), ('assessor', 'Field assessor', 'text'),
                ('borrowers', 'Borrowers', 'number')]

VALUATION_GROUPS = OrderedDict([
    ('doer', ('Valued by', by('doer_id', 'doer', 'Not recorded'))),
    ('status', ('Valuation status', status_of(VALUATION_STATUS))),
    ('month', ('Month valued', month('valued'))),
    ('service', ('Service rendered', by('service_id', 'service'))),
    ('client', ('Client', lambda r: (str(r['office_id']), ', '.join(x for x in (r['office'], r['branch']) if x) or 'Not recorded'))),
    ('area', ('Area', lambda r: ((r['district'] or '').lower(), ', '.join(x for x in (r['district'], r['state']) if x) or 'Area not recorded'))),
])
VALUATION_MEASURES = [('valuations', 'Valuations', 'count'),
                      ('pending', 'Being filled in', 'count', lambda r: r['status_code'] == 'Pending'),
                      ('submitted', 'Submitted', 'count', lambda r: r['status_code'] == 'Submit'),
                      ('reverted', 'Sent back', 'count', lambda r: r['status_code'] == 'Revert'),
                      ('held', 'On hold', 'count', lambda r: r['status_code'] == 'Hold'),
                      ('cancelled', 'Cancelled', 'count', lambda r: r['status_code'] == 'Cancel')]
VALUATION_COLUMNS = [('report', 'Report', 'text'), ('lead', 'Lead', 'text'), ('valued', 'Valued', 'date'), ('status', 'Status', 'text'),
                     ('office', 'Client', 'text'), ('borrower', 'Client customer', 'text'), ('service', 'Service', 'text'),
                     ('doer', 'Valued by', 'text')]

report('leads', number='1', title='Month-wise leads', section='Work',
       description='Leads received, by status. Deleted leads are not counted.', date_label='Received',
       rows=leads, groups=LEAD_GROUPS, default_group='status', measures=LEAD_MEASURES[:1] + LEAD_MEASURES[5:], columns=LEAD_COLUMNS)
report('lead-mis', number='6', title='Lead MIS by client', section='Work',
       description='Leads each client sent, and where they stand.', date_label='Received',
       rows=leads, groups=OrderedDict([('client', LEAD_GROUPS['client']), *[(k, v) for k, v in LEAD_GROUPS.items() if k != 'client']]),
       default_group='client', measures=LEAD_MEASURES, columns=LEAD_COLUMNS)
report('valuations', number='2', title='Month-wise valuations', section='Work',
       description='Valuations by status.', date_label='Valuation date',
       rows=valuations, groups=OrderedDict([('status', VALUATION_GROUPS['status']), *[(k, v) for k, v in VALUATION_GROUPS.items() if k != 'status']]),
       default_group='status', measures=VALUATION_MEASURES[:1], columns=VALUATION_COLUMNS)
report('doer-wise', number='4', title='Doer-wise valuations', section='Work',
       description='Valuations each person carried out, and where they stand.', date_label='Valuation date',
       rows=valuations, groups=VALUATION_GROUPS, default_group='doer', measures=VALUATION_MEASURES, columns=VALUATION_COLUMNS)
report('service-rendered', number='5', title='Service rendered', section='Work',
       description='Invoices by the service rendered, counted once per invoice.', date_label='Invoice date',
       rows=lambda u, f: invoices(u, f),
       groups=OrderedDict([('service', INVOICE_GROUPS['service']),
                           ('subtype', ('Service and type', lambda r: (f"{r['service_id']}:{r['subtype'] or ''}", ', '.join(x for x in (r['service'], r['subtype']) if x) or 'Not recorded'))),
                           *[(k, v) for k, v in INVOICE_GROUPS.items() if k != 'service']]),
       default_group='service', measures=[('invoices', 'Invoices', 'count'), ('billed', 'Invoiced', 'money')], columns=INVOICE_COLUMNS)
report('cancelled-valuations', number='9', title='Cancelled valuations', section='Work',
       description='Every cancelled valuation, with the reason given.', date_label='Cancelled on',
       rows=lambda u, f: valuations(u, f, cancelled=True),
       groups=OrderedDict([('client', VALUATION_GROUPS['client']), ('doer', VALUATION_GROUPS['doer']),
                           ('month', ('Month cancelled', month('cancelled_on'))), ('area', VALUATION_GROUPS['area'])]),
       default_group='client', measures=[('cancelled', 'Cancelled', 'count')],
       columns=[('lead', 'Lead', 'text'), ('work_order', 'Work order', 'text'), ('report', 'Report', 'text'), ('office', 'Client', 'text'),
                ('ifsc', 'IFSC', 'text'), ('borrower', 'Client customer', 'text'), ('doer', 'Valued by', 'text'),
                ('cancelled_on', 'Cancelled on', 'date'), ('reason', 'Reason', 'text')])


def offline_invoices(user, f):
    """Offline invoices (2020-21), dated by invoice date, with their balance: the
    total less the advance and recorded payments. Visible only to a user who may
    see offline invoices. The legacy offline billing query grouped by a table it
    did not select from and failed every time it ran."""
    from apps.billing.services import offline_queryset
    qs = offline_queryset(user)
    if f['from']:
        qs = qs.filter(issued_date__gte=f['from'])
    if f['to']:
        qs = qs.filter(issued_date__lte=f['to'])
    if f['q']:
        qs = qs.filter(Q(number__icontains=f['q']) | Q(billed_to_name__icontains=f['q']) | Q(billed_customer_name__icontains=f['q'])
                       | Q(reference_report__icontains=f['q']) | Q(reference_lead__icontains=f['q']))
    rows = []
    for r in qs.values('pk', 'number', 'issued_date', 'billed_amount', 'bad_debt_amount', 'outstanding', 'billed_to_name',
                       'billed_branch_name', 'billed_customer_name', 'reference_report', 'reference_lead', 'service__name', 'service_id',
                       'liable_employee__name', 'liable_employee_id', 'doer_employee__name', 'doer_employee_id'):
        billed, owed = money(r['billed_amount']), money(r['outstanding'])
        rows.append({'id': r['pk'], 'invoice': r['number'], 'issued': r['issued_date'], 'billed': billed,
                     'paid': billed - money(r['bad_debt_amount']) - owed, 'written_off': money(r['bad_debt_amount']),
                     'outstanding': max(owed, ZERO), 'client': (r['billed_to_name'] or '').strip(), 'branch': r['billed_branch_name'],
                     'borrower': r['billed_customer_name'], 'report': r['reference_report'], 'lead': r['reference_lead'],
                     'service': r['service__name'], 'service_id': r['service_id'], 'liable': r['liable_employee__name'],
                     'liable_id': r['liable_employee_id'], 'doer': r['doer_employee__name'], 'doer_id': r['doer_employee_id']})
    return rows


def targets(user, f):
    """Each field assessor's target for a financial year, against what they
    achieved: standing invoices issued within that year on valuations they were
    liable for, as the legacy targets report counted them.

    One assessor holds two targets for one year. The legacy report grouped by year
    and assessor, so both rows joined the same invoices and that assessor's
    achievement was counted twice. Here the most recent target applies, the other
    is shown as superseded, and achievement is counted once."""
    qs = m.EmployeeTarget.objects.select_related('employee').filter(legacy_status__in=('1', ''))
    who = scoped_employee(user)
    if who is not None:
        qs = qs.filter(employee=who) if who is not None and hasattr(who, 'pk') else qs.none()
    if f['from']:
        qs = qs.filter(period_end__gte=f['from'])
    if f['to']:
        qs = qs.filter(period_start__lte=f['to'])
    import json
    source_id = {str(t): int(json.loads(k)[0][1]) for k, t in m.SourceIdentity.objects.filter(
        environment='main', schema='lead_mngt', table='employee_target').values_list('key', 'target_id')}

    def recency(t):
        # Numbers, not text ("12" is newer than "9"); a target set here is newer than any import.
        return (1, t.created_at) if str(t.pk) not in source_id else (0, source_id[str(t.pk)])
    latest = {}
    for t in qs:
        key = (t.employee_id, t.financial_year)
        if key not in latest or recency(t) > latest[key][0]:
            latest[key] = (recency(t), t)
    achieved = {}
    for r in bank_reports(user, {**f, 'from': None, 'to': None, 'q': ''}):
        if r['issued']:
            achieved.setdefault(r['liable_id'], []).append((r['issued'], r['billed']))
    rows = []
    for (employee_id, year), (_, t) in latest.items():
        inside = [(d, b) for d, b in achieved.get(str(employee_id), []) if t.period_start <= d <= t.period_end] if t.period_start else []
        amount = sum((b for _, b in inside), ZERO)
        rows.append({'id': t.pk, 'employee': t.employee.name, 'employee_id': str(employee_id),
                     'year': f"{t.period_start:%Y}-{t.period_end:%y}" if t.period_start else year, 'year_key': year,
                     'target_cases': t.target_cases or 0, 'achieved_cases': len(inside), 'target_amount': money(t.target_amount),
                     'achieved_amount': money(amount),
                     'share': (amount * 100 / t.target_amount).quantize(Decimal('0.1')) if t.target_amount else None,
                     'superseded': sum(1 for x in qs if (x.employee_id, x.financial_year) == (employee_id, year)) - 1})
    return rows


report('offline-billing', number='10', title='Offline billing', section='Billing',
       description='Invoices raised outside the system in 2020-21, with what is still owed.', date_label='Invoice date',
       rows=offline_invoices,
       groups=OrderedDict([('client', ('Billed to', lambda r: (r['client'].lower(), ', '.join(x for x in (r['client'], r['branch']) if x) or 'Not recorded'))),
                           ('customer', ('Client customer', lambda r: ((r['borrower'] or '').strip().lower(), (r['borrower'] or '').strip() or 'Not recorded'))),
                           ('liable', ('Liable field assessor', by('liable_id', 'liable', 'Not recorded'))),
                           ('doer', ('Valued by', by('doer_id', 'doer', 'Not recorded'))),
                           ('service', ('Service rendered', by('service_id', 'service'))),
                           ('month', ('Month', month('issued')))]),
       default_group='client', sort='outstanding', measures=MONEY,
       columns=[('invoice', 'Invoice', 'text'), ('issued', 'Date', 'date'), ('client', 'Billed to', 'text'), ('borrower', 'Client customer', 'text'),
                ('report', 'Report reference', 'text'), ('liable', 'Liable field assessor', 'text'),
                ('billed', 'Invoiced', 'money'), ('paid', 'Received', 'money'), ('outstanding', 'Outstanding', 'money')])
report('fa-targets', number='11', title="Field assessors' financial targets", section='Billing',
       description='Each field assessor\'s target for the year against what they achieved, counting invoices on valuations they were liable for.',
       date_label='Financial year', rows=targets,
       groups=OrderedDict([('year', ('Financial year', lambda r: (r['year'], r['year']))),
                           ('employee', ('Field assessor', by('employee_id', 'employee')))]),
       default_group='year', sort='target_amount',
       measures=[('target_cases', 'Target cases', 'number'), ('achieved_cases', 'Cases achieved', 'number'),
                 ('target_amount', 'Target amount', 'money'), ('achieved_amount', 'Amount achieved', 'money'),
                 ('share', 'Achieved', 'percent', ('achieved_amount', 'target_amount'))],
       columns=[('employee', 'Field assessor', 'text'), ('year', 'Financial year', 'text'), ('target_cases', 'Target cases', 'number'),
                ('achieved_cases', 'Cases achieved', 'number'), ('target_amount', 'Target amount', 'money'),
                ('achieved_amount', 'Amount achieved', 'money'), ('share', 'Achieved', 'percent'), ('superseded', 'Superseded targets', 'number')])


# --- the engine --------------------------------------------------------------

def filters_from(request):
    def day(name):
        v = request.GET.get(name)
        if not v:
            return None
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            raise IntakeError(f'Enter {name} as YYYY-MM-DD')
    f = {'from': day('from'), 'to': day('to')}
    if f['from'] and f['to'] and f['from'] > f['to']:
        raise IntakeError('The start date is after the end date')
    f.update({k: (request.GET.get(k) or '').strip() for k in ('office', 'service', 'assessor', 'division', 'district', 'q')})
    return f


def run(spec, user, f, group):
    groups = spec['groups']
    if group not in groups:
        group = spec['default_group']
    label, key_of = groups[group]
    rows = spec['rows'](user, f)
    buckets, totals = OrderedDict(), {x[0]: ZERO if x[2] == 'money' else 0 for x in spec['measures']}
    for r in rows:
        k, name = key_of(r)
        b = buckets.setdefault(k, {'key': k, 'label': name, 'values': {x[0]: ZERO if x[2] == 'money' else 0 for x in spec['measures']}, 'rows': []})
        b['rows'].append(r)
        for measure in spec['measures']:
            m_, kind = measure[0], measure[2]
            if kind == 'percent':
                continue                                          # derived once the group is totalled
            when = measure[3] if len(measure) > 3 else None
            v = (1 if (when is None or when(r)) else 0) if kind == 'count' else r.get(m_, ZERO)
            b['values'][m_] += v
            totals[m_] += v
    for measure in spec['measures']:
        if measure[2] == 'percent':
            num, den = measure[3]
            for values in [b['values'] for b in buckets.values()] + [totals]:
                values[measure[0]] = (Decimal(values[num]) * 100 / Decimal(values[den])).quantize(Decimal('0.1')) if values[den] else None
    # Sequences keep their natural order (status stages, months, age bands); anything
    # else runs largest first, by the report's leading money measure or, failing
    # that, its first count. Unrecorded values always come last.
    natural = group in ('age', 'month', 'status', 'year')
    money_first = spec.get('sort') or next((x[0] for x in spec['measures'] if x[2] == 'money'), spec['measures'][0][0])
    unknown = ('Not recorded', 'Not assigned', 'No division', 'Date unknown', 'Area not recorded')
    ordered = sorted(buckets.values(), key=lambda b: (b['label'] in unknown, b['key'] if natural else '',
                                                     0 if natural else -b['values'][money_first], b['label']))
    return group, label, ordered, totals


def as_json(v):
    if isinstance(v, Decimal):
        return str(v.quantize(Decimal('0.01')))
    if isinstance(v, datetime.date):
        return v.isoformat()
    return v


def meta(spec):
    return {'key': spec['key'], 'number': spec['number'], 'title': spec['title'], 'section': spec['section'],
            'description': spec['description'], 'date_label': spec['date_label'],
            # 'groupings' are the choices; a result's 'groups' are the grouped figures.
            'groupings': [{'key': k, 'label': v[0]} for k, v in spec['groups'].items()], 'default_group': spec['default_group'],
            'measures': [{'key': x[0], 'label': x[1], 'kind': x[2]} for x in spec['measures']],
            'columns': [{'key': k, 'label': l, 'kind': kind} for k, l, kind in spec['columns']]}


def spec_of(key):
    if key not in REPORTS:
        raise IntakeError('Report not found', 404)
    return REPORTS[key]


@endpoint(['GET'])
def catalogue(request):
    return JsonResponse({'reports': [meta(s) for s in REPORTS.values()]})


@endpoint(['GET'])
def result(request, key):
    spec = spec_of(key)
    f = filters_from(request)
    group, label, groups, totals = run(spec, request.user, f, request.GET.get('group', ''))
    body = {**meta(spec), 'group': group, 'group_label': label,
            'filters': {k: as_json(v) for k, v in f.items()},
            'groups': [{'key': g['key'], 'label': g['label'], 'values': {k: as_json(v) for k, v in g['values'].items()}} for g in groups],
            'totals': {k: as_json(v) for k, v in totals.items()}}
    within = request.GET.get('within')
    if within is not None:
        chosen = next((g for g in groups if g['key'] == within), None)
        rows = chosen['rows'] if chosen else []
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except ValueError:
            page = 1
        body['detail'] = {'group': within, 'label': chosen['label'] if chosen else '', 'total': len(rows), 'page': page,
                          'page_size': PAGE_SIZE,
                          'rows': [{c: as_json(r.get(c)) for c, _, _ in spec['columns']} for r in rows[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]]}
    return JsonResponse(body)


@endpoint(['GET'])
def export(request, key):
    from .export import workbook
    spec = spec_of(key)
    f = filters_from(request)
    group, label, groups, totals = run(spec, request.user, f, request.GET.get('group', ''))
    return workbook(spec, f, label, groups, totals)
