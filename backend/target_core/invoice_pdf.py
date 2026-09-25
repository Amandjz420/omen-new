"""Render a tax invoice, or the credit note that reverses one.

Carries what the legacy invoice (InvoiceNewTestUtil) prints: invoice number and
dates; the billed client with branch, IFSC and GSTIN; the case (borrower, lead,
work order and report numbers, enquiry mode); who pays; each charge with its
CGST, SGST or IGST; the totals in figures and words; and the Omen account to pay
into. It adds what a GST tax invoice needs and the legacy one left implicit:
Omen's GSTIN, the place of supply and the rates.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import models as m
from .bank_report_pdf import LETTERHEAD, rupees
from .words import amount_words

_base = getSampleStyleSheet()
TITLE = ParagraphStyle('t', parent=_base['Title'], fontSize=14, spaceAfter=2)
BODY = ParagraphStyle('b', parent=_base['Normal'], fontSize=9, leading=12)
SMALL = ParagraphStyle('s', parent=BODY, fontSize=8, leading=10)


def t(v):
    return escape('' if v is None else str(v))


def money(v):
    return f'{float(v or 0):,.2f}'


def grid(rows, widths, bold_last=False):
    table = Table([[c if isinstance(c, Paragraph) else Paragraph(t(c), SMALL) for c in r] for r in rows], colWidths=widths, repeatRows=1)
    style = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
             ('VALIGN', (0, 0), (-1, -1), 'TOP')]
    if bold_last:
        style.append(('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')))
    table.setStyle(TableStyle(style))
    return table


def render(invoice, credit=None):
    from .invoices import FIRM_GSTIN, party_gstin
    v = invoice.valuation
    case = v.case if v else None
    office = invoice.office or (case.lead.office if case else None)
    full = 176 * mm
    story = []
    if LETTERHEAD.exists():
        story.append(Image(str(LETTERHEAD), width=full * .8, height=full * .8 * 206 / 590))
    story += [Paragraph('CREDIT NOTE' if credit else 'TAX INVOICE', TITLE),
              Paragraph(f'<b>GSTIN:</b> {t(FIRM_GSTIN)}', BODY), Spacer(1, 6)]
    head = [['Invoice No.', invoice.number, 'Invoice Date', invoice.issued_date.strftime('%d-%m-%Y') if invoice.issued_date else '']]
    if credit:
        head.insert(0, ['Credit Note No.', credit.number, 'Credit Note Date', credit.issued_on.strftime('%d-%m-%Y')])
    else:
        head.append(['Due Date', invoice.due_date.strftime('%d-%m-%Y') if invoice.due_date else '',
                     'Place of Supply', invoice.get_place_of_supply_display() if invoice.place_of_supply else ''])
    story.append(grid([[Paragraph(f'<b>{t(a)}</b>', SMALL), t(b), Paragraph(f'<b>{t(c)}</b>', SMALL), t(d)] for a, b, c, d in head],
                      [full * .2, full * .3, full * .2, full * .3]))
    gstin = party_gstin(v, invoice.gstin_party or 1, invoice.other_gstin) if v else invoice.other_gstin
    billed = [f'<b>{t(office.name if office else "")}</b>']
    if office:
        billed += [t(x) for x in (office.branch_name, office.address) if x]
        if office.ifsc:
            billed.append(f'IFSC: {t(office.ifsc)}')
    billed.append(f'GSTIN ({t(invoice.get_gstin_party_display() if invoice.gstin_party else "Client")}): {t(gstin) or "—"}')
    case_lines = []
    if case:
        order = m.WorkOrder.objects.filter(borrower_id=case.borrower_id).order_by('created_at').first()
        case_lines = [f'<b>Borrower:</b> {t(case.borrower.name if case.borrower_id else "")}',
                      f'<b>Lead:</b> {t(case.lead.number)} &nbsp; <b>Work order:</b> {t(order.number if order else "")}',
                      f'<b>Report:</b> {t(v.report_number)} &nbsp; <b>Service:</b> {t(case.service.name)}',
                      f'<b>Enquiry:</b> {t(case.lead.get_enquiry_mode_display() if case.lead.enquiry_mode else "")}'
                      f' &nbsp; <b>Paid by:</b> {t(invoice.get_payer_display() if invoice.payer else "")}']
    story += [Spacer(1, 6), Table([[Paragraph('<br/>'.join(billed), BODY), Paragraph('<br/>'.join(case_lines), BODY)]],
                                  colWidths=[full / 2, full / 2], style=[('VALIGN', (0, 0), (-1, -1), 'TOP')]), Spacer(1, 6)]

    lines = list(invoice.lines.order_by('position'))
    rows = [['#', 'Particulars', 'Taxable', 'CGST 9%', 'SGST 9%', 'IGST 18%', 'Total']]
    if lines:
        data = [(l.description, l.net_amount, l.cgst, l.sgst, l.igst, l.total_amount) for l in lines]
    else:
        data = [((c.charge_type.name.strip() if c.charge_type else 'Charge'), c.amount, c.cgst, c.sgst, c.igst, c.total_amount)
                for c in m.ValuationCharge.objects.filter(valuation=v).select_related('charge_type').order_by('charge_type__source_sequence') if c.amount] if v else []
    sums = [0, 0, 0, 0, 0]
    for n, (desc, amt, cg, sg, ig, tot) in enumerate(data, 1):
        vals = [float(x or 0) for x in (amt, cg, sg, ig, tot)]
        sums = [a + b for a, b in zip(sums, vals)]
        rows.append([n, desc] + [money(x) for x in vals])
    rows.append(['', 'Total'] + [money(x) for x in sums])
    story.append(grid(rows, [full * w for w in (.05, .31, .13, .12, .12, .13, .14)], bold_last=True))
    total = float(credit.total_amount if credit else invoice.billed_amount or 0)
    story += [Spacer(1, 6), Paragraph(f'<b>{"Amount credited" if credit else "Invoice total"}:</b> Rs. {t(money(total))} '
                                      f'(Rupees {t(amount_words(round(total)))} only)', BODY)]
    if credit:
        story += [Paragraph(f'<b>Against invoice:</b> {t(invoice.number)} dated {t(invoice.issued_date)}', BODY),
                  Paragraph(f'<b>Reason:</b> {t(credit.reason)}', BODY)]
        if float(credit.refund_due or 0) > 0:
            story.append(Paragraph(f'<b>Amount received and due for refund or adjustment:</b> Rs. {t(money(credit.refund_due))}', BODY))
    else:
        paid, due = float(invoice.legacy_paid_amount or 0), float(invoice.legacy_remaining_amount or 0)
        story += [Paragraph(f'<b>Advance received:</b> Rs. {t(money(paid))}', BODY),
                  Paragraph(f'<b>Balance due:</b> Rs. {t(money(due))} (Rupees {t(amount_words(round(due)))} only)', BODY)]
        if float(invoice.excess_amount or 0) > 0:
            story.append(Paragraph(f'<b>Received in excess:</b> Rs. {t(money(invoice.excess_amount))}', BODY))
        a = invoice.issuer_account
        if a:
            story += [Spacer(1, 8), Paragraph('<b>Please pay into:</b>', BODY),
                      Paragraph(f'{t(a.name.strip())} &nbsp; A/c No. {t(a.account_number)} &nbsp; IFSC {t(a.ifsc_code)}', BODY)]
            if a.branch_address:
                story.append(Paragraph(t(a.branch_address), SMALL))
    story += [Spacer(1, 24), Paragraph('For Omen Assessors', BODY), Spacer(1, 18), Paragraph('Authorised Signatory', BODY)]
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                      title=f'{"Credit Note " + credit.number if credit else "Invoice " + invoice.number}',
                      author='Omen Assessors').build(story)
    return buffer.getvalue()
