"""Render the work-order letter.

Reproduces the five sections of the legacy OrderUtil.prepareLeadHTML letter,
which is addressed to Omen Assessors by the client placing the order. Two
spelling errors in the legacy text ("refernece", "citied") are corrected; the
wording and structure are otherwise the legacy letter's.

Every value is escaped, since reportlab paragraphs interpret markup and names
and addresses are free text entered by operators.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from target_core import models as m
from apps.migration_pipeline.services import source_key

FIRM = ['Omen Assessors', 'F-6, 1st Floor, Sanchi Complex,', 'Opposite Board Office, Shivaji Nagar,',
        'Bhopal (M.P.) 462016']

_base = getSampleStyleSheet()
TITLE = ParagraphStyle('t', parent=_base['Title'], fontSize=14, spaceAfter=4)
BODY = ParagraphStyle('b', parent=_base['Normal'], fontSize=9, leading=12)
HEAD = ParagraphStyle('h', parent=BODY, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=3)
CELL = ParagraphStyle('c', parent=BODY, fontSize=8, leading=10)


def text(value):
    return escape('' if value is None else str(value))


def resolve_names(table, model, codes):
    """Legacy comma-separated source ids -> the names of their migrated records."""
    ids = [c.strip() for c in (codes or '').split(',') if c.strip()]
    if not ids:
        return ''
    keys = {source_key(i): i for i in ids}
    targets = dict(m.SourceIdentity.objects.filter(environment='main', schema='lead_mngt', table=table,
                                                   key__in=list(keys)).values_list('key', 'target_id'))
    names = dict(model.objects.filter(pk__in=targets.values()).values_list('pk', 'name'))
    return ', '.join(names.get(targets.get(k), f'#{i}') for k, i in keys.items())


def grid(header, rows, widths):
    data = [[Paragraph(f'<b>{text(h)}</b>', CELL) for h in header]]
    data += [[Paragraph(text(v), CELL) for v in row] for row in rows] or [[Paragraph('—', CELL)] + [''] * (len(header) - 1)]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return table


def money(value):
    return f'Rs. {value:,.2f}' if value is not None else ''


def payment_terms(borrower, lead):
    """Client review 2026-11-05: the terms of payment, from the fee agreement recorded
    with the client's customer: who pays, the fee, how, by whom and by when."""
    if borrower.payer == 1:
        payer = f'The client{": " + borrower.payer_name if borrower.payer_name else ""}'
    elif borrower.payer == 2:
        payer = f"The client's customer (applicant): {borrower.name}"
    else:
        payer = ''
    if borrower.fee_basis == 2:
        fee = f'Fixed amount of {money(borrower.agreed_fee)}, GST extra as applicable'
    elif borrower.fee_basis == 1:
        fee = "As per the client's circular / approved fee schedule, GST extra as applicable"
    else:
        fee = ''
    responsible = ', '.join(x for x in (borrower.payment_reference_name, borrower.payment_reference_number) if x)
    rows = [('Payable by', payer), ('Fee', fee),
            ('Mode of payment', borrower.get_customer_payment_method_display() if borrower.customer_payment_method else ''),
            ('Person responsible for payment', responsible),
            ('Payment due by', borrower.pay_by_date.strftime('%d-%m-%Y') if borrower.pay_by_date else ''),
            ('GST No. for billing', borrower.gst_number)]
    return [(label, value) for label, value in rows if value]


def signature_block(lead, width):
    """A blank block for the client's authorised signatory, signed on paper."""
    office = lead.office
    client = ', '.join(x for x in (office.name, office.branch_name) if x) if office else ''
    lines = [Paragraph(f'<b>For {text(client)}</b>' if client else '<b>For the client</b>', BODY), Spacer(1, 30),
             Paragraph('Authorised Signatory', BODY), Spacer(1, 6),
             Paragraph('Name: ____________________________', BODY), Spacer(1, 4),
             Paragraph('Designation: _______________________', BODY), Spacer(1, 4),
             Paragraph('Date: ____________________________', BODY), Spacer(1, 4),
             Paragraph('Seal:', BODY)]
    table = Table([['', lines]], colWidths=[width * .45, width * .55])
    table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOX', (1, 0), (1, 0), 0.5, colors.black),
                               ('LEFTPADDING', (1, 0), (1, 0), 8), ('TOPPADDING', (1, 0), (1, 0), 6),
                               ('BOTTOMPADDING', (1, 0), (1, 0), 8)]))
    return table


def render(work_order):
    borrower, lead = work_order.borrower, work_order.lead
    contact = lead.contact
    cases = list(m.Case.objects.filter(borrower=borrower).select_related('service', 'subtype').order_by('created_at', 'id'))
    full = 176 * mm

    story = [Paragraph('Work Order', TITLE),
             Paragraph(f'<b>OA Work Order No.:</b> {text(work_order.number)}', BODY),
             Paragraph(f'<b>Date:</b> {text(lead.received_date.strftime("%d-%m-%Y") if lead.received_date else "")}', BODY),
             Paragraph('<b>Client Work Order No.:</b>', BODY), Spacer(1, 6),
             Paragraph('To,', BODY)]
    story += [Paragraph(text(line), BODY) for line in FIRM]
    story += [Spacer(1, 6), Paragraph('Dear Sir,', BODY),
              Paragraph(f'With reference to the {text(work_order.number)} cited above, we are pleased to place '
                        f'an order for the service mentioned below:', BODY)]

    story += [Paragraph('(1). Orderer Information:', HEAD),
              grid(['Name', 'Mobile No'], [[contact.name if contact else '', contact.phone if contact else '']],
                   [full * .6, full * .4])]
    story += [Paragraph('(2). Client Customer Detail:', HEAD),
              grid(['Client Customer Name', 'Email Id', 'Contact No.', 'No. Of Cases'],
                   [[borrower.name, borrower.email, borrower.contact_number, borrower.property_count]],
                   [full * .35, full * .3, full * .2, full * .15])]
    story += [Paragraph('(3). Payment Responsibility:', HEAD),
              grid(['Paid By', 'Paid By Mode', 'Payment By Mode'],
                   [[borrower.get_payer_display() if borrower.payer else '',
                     borrower.get_fee_basis_display() if borrower.fee_basis else '',
                     borrower.get_customer_payment_method_display() if borrower.customer_payment_method else '']],
                   [full / 3] * 3)]
    story += [Paragraph('(4). Properties Information:', HEAD),
              grid(['SNo.', "Client's Customer Name", 'Service Type', 'Service Sub Type', 'Usage of Report',
                    'Scrutiny Document', 'Remarks'],
                   [[n, borrower.name, c.service.name, c.subtype.name if c.subtype else '',
                     resolve_names('usage_of_reports', m.ReportUsage, c.usage_of_report_code),
                     resolve_names('scrutiny_document', m.ScrutinyRequirement, c.scrutiny_document_code),
                     c.remarks] for n, c in enumerate(cases, 1)],
                   [full * w for w in (.06, .17, .14, .14, .17, .17, .15)])]
    story += [Paragraph('(5). Properties Address Information:', HEAD),
              grid(['SNo.', 'State', 'District', 'Pin Code', 'Address'],
                   [[n, c.asset_state, c.asset_district, c.asset_pin_code, c.asset_address]
                    for n, c in enumerate(cases, 1)],
                   [full * w for w in (.06, .16, .18, .12, .48)])]
    terms = payment_terms(borrower, lead)
    story += [Paragraph('(6). Terms of Payment:', HEAD),
              grid(['Term', 'Detail'], terms, [full * .32, full * .68]) if terms
              else Paragraph('Not recorded.', BODY)]
    story += [Spacer(1, 18), KeepTogether([signature_block(lead, full)])]

    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                      topMargin=15 * mm, bottomMargin=15 * mm,
                      title=f'Work Order {work_order.number}', author='Omen Assessors').build(story)
    return buffer.getvalue()
