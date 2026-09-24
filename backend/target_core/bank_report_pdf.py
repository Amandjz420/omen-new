"""Render the bank report.

Reproduces ValuationBankReportUtil.prepareLeadHTML (bank clients) and
prepareReportHTML (others): references, addressee, subject, the template body,
the valuer's opinion stating the four values, the signature block, the bank's
countersignature block, the enclosure list, the photographs, the certificate, and
the firm's standing text on valuation terms, conditions, assumptions and sources.

The standing text is the firm's own legal wording and is reproduced as written,
including "Sales comparison approach is used for:", which the legacy report
prints with nothing after it. Presentation is corrected where the legacy layout
was plainly broken: amounts print with Indian digit grouping and read
"(Rupees ... only)" around the words instead of "...Thousand(Rupees only)".

Every value is escaped, since templates and answers are free text.
"""
import io
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import models as m
from .valuations import KINDS, LIVE, answer_of, number, options_of
from .words import amount_words

FIRM = ['Omen Assessors', 'F-6, 1st Floor, Sanchi Complex, Opposite Board Office, Shivaji Nagar, Bhopal (M.P.) 462016']
PHOTO_LABELS = {1: 'Front', 2: 'Inside', 3: 'Right View', 4: 'Left View', 5: 'Location Plan', 6: 'Site Plan', 7: 'Other'}

_base = getSampleStyleSheet()
TITLE = ParagraphStyle('t', parent=_base['Title'], fontSize=14, spaceAfter=4)
BODY = ParagraphStyle('b', parent=_base['Normal'], fontSize=9, leading=12)
SMALL = ParagraphStyle('s', parent=BODY, fontSize=8, leading=10)
HEAD = ParagraphStyle('h', parent=BODY, fontName='Helvetica-Bold', fontSize=10, spaceBefore=8, spaceAfter=3)
LABEL = ParagraphStyle('l', parent=BODY, fontName='Helvetica-Bold')
BULLET = ParagraphStyle('u', parent=BODY, leftIndent=12, bulletIndent=2)

STANDING = [
    ('Our understanding of various valuations:-', [
        '<b>Fair Market Value</b> An amount likely to be fetched by willing owner of his property through open market, '
        'in normal circumstances. These are normally determined by sales comparison and cost approaches.',
        '<b>Estimated Realizable Value</b> An amount likely to be fetched by mortgager or financial institute of a '
        'property through open market in normal circumstances.',
        '<b>Distress/Forced Sale Value</b> An amount likely to be fetched by mortgager or financial institution of a '
        'property through open market in deteriorated circumstances. Normally settlement or auction of NPA is done on '
        'basis of this value.',
        '<b>Government Guide Line Value</b> It is the value specified by government once a year, and is applicable '
        'complete financial year (April to March). Based on this value, minimum stamp duty is to be paid for '
        'registration deed.']),
    ('Limiting conditions:-', [
        'We are not responsible for matters of legal nature affecting valuation of property.',
        'Measurements done of property are under constraint site conditions and we strive for the accuracy to the '
        'extent required for valuation.',
        'Government enactment/ acquisition details are given on the basis of local enquiry &amp; site conditions.',
        'Comment on remaining life of building is on basis of physical inspection of site, no any structural design '
        'or details were examined.']),
    ('Assumption considered:-', [
        'That property is legally marketable, mortgageable &amp; not coming under acquisition certified so by '
        'bank\u2019s empanelled advocate.',
        'Information and documents submitted by party/bank, are true and correct.']),
    ('Followings were used in preparing this report:-', [
        'Facts &amp; figures of documents made available to us.', 'Details &amp; information of government sites.',
        'Physical condition &amp; specification of property.', 'Information &amp; data collected from field survey of site.']),
    ('Valuation Approaches:-', [
        '<b>Sales comparison approach</b> is used for:',
        'The valuation report is an opinion made in good faith without any prejudice, all due care is taken in its '
        'preparation.',
        'The valuation amount varies with purpose and time, so this report should not be used for other purpose than '
        'mentioned above.'])]


def t(value):
    return escape('' if value is None else str(value))


def rupees(value):
    """Indian digit grouping of the rounded amount: 3850000 -> 38,50,000."""
    n = round(float(value or 0))
    sign, digits = ('-' if n < 0 else ''), str(abs(n))
    if len(digits) <= 3:
        return sign + digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return sign + ','.join(([head] if head else []) + groups) + ',' + tail


def stated(value):
    words = amount_words(round(float(value or 0)))
    return f'Rs. {rupees(value)} (Rupees {words} only)'


def grid(rows, widths):
    table = Table([[c if isinstance(c, Paragraph) else Paragraph(t(c), SMALL) for c in r] for r in rows],
                  colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eeeeee')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return table


def line_flowables(line, answers, full):
    """One template line: its label, then the answer the way its type prints."""
    q = line.question
    kind = KINDS.get(q.answer_type, 'text')
    label = f'{t(line.indexing)} {t(line.output_label)}'.strip()
    before, after = t(line.content_before), t(line.content_after)
    out = [Paragraph(f'<b>{label}</b>', BODY)] if label else []
    options = options_of(q)
    if kind in ('grid', 'formula'):
        value = answer_of(q, answers, options)
        header = ['No.'] + [o.value.strip() for o in options]
        body = [[str(r['group'])] + [r['cells'].get(str(o.pk), '') for o in options] for r in value['rows']]
        if before:
            out.append(Paragraph(before, BODY))
        if body:
            n = len(header)
            out.append(grid([header] + body, [full * .07] + [full * .93 / (n - 1)] * (n - 1)))
        if after:
            out.append(Paragraph(after, BODY))
    elif kind == 'sum':
        value = answer_of(q, answers, options)
        rows = [['Particulars', 'Value']] + [[o.value.strip(), value['values'].get(str(o.pk), '')] for o in options]
        rows.append(['Total', f"{value['total']:.2f}"])
        if before:
            out.append(Paragraph(before, BODY))
        out.append(grid(rows, [full * .7, full * .3]))
        if after:
            out.append(Paragraph(after, BODY))
    elif kind == 'multiple':
        values = [a.value for a in answers if (a.value or '').strip()]
        out.append(Paragraph(f'{before} {t(", ".join(values))} {after}'.strip(), BODY))
    else:
        values = [a.value for a in answers if (a.value or '').strip()]
        for v in values or ['']:
            out.append(Paragraph(f'{before} {t(v)} {after}'.strip(), BODY))
    return out


def template_lines(template):
    """The lines a report prints. As in the legacy queries, a line prints only
    under a live heading and with a live question; lines with no heading or no
    question never appeared in a legacy report."""
    return (m.ReportTemplateLine.objects.filter(template=template, question__isnull=False,
                                                question__legacy_deleted__in=LIVE, heading__isnull=False,
                                                heading__legacy_deleted__in=LIVE)
            .select_related('question', 'heading').order_by('heading__display_order', 'heading__name', 'sequence', 'id'))


def body_flowables(template, answers, full):
    out, current = [], None
    for line in template_lines(template):
        if line.heading_id != current:
            current = line.heading_id
            out.append(Paragraph(t(line.heading.name), HEAD))
        out += line_flowables(line, answers.get(line.question_id, []), full)
    return out


def photo_flowables(valuation, full):
    cells, out = [], []
    for p in m.ValuationAttachment.objects.filter(valuation=valuation).select_related('document').order_by('attachment_type', 'created_at'):
        code = int(p.attachment_type) if (p.attachment_type or '').isdigit() else None
        caption = Paragraph(f'<b>{t(PHOTO_LABELS.get(code, "Photo"))}</b> {t(p.name)}', SMALL)
        doc = p.document
        path = Path(settings.MEDIA_ROOT) / doc.storage_key if doc and doc.storage_provider == 'local' else None
        if path and path.exists():
            try:
                cells.append([Image(str(path), width=full / 2 - 6 * mm, height=(full / 2 - 6 * mm) * .75, kind='proportional'), caption])
                continue
            except Exception:
                pass
        cells.append([Paragraph('Photograph held in legacy storage', SMALL), caption])
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2] + ([['', '']] if len(cells[i:i + 2]) == 1 else [])
        out.append(Table([[pair[0][0], pair[1][0]], [pair[0][1], pair[1][1]]], colWidths=[full / 2] * 2))
    return out


def render(report, template, bank_client):
    valuation, case = report.valuation, report.valuation.case
    office, full = case.lead.office, 176 * mm
    story = [Paragraph(t(FIRM[0]), TITLE), Paragraph(t(FIRM[1]), SMALL), Spacer(1, 6)]
    number = t(valuation.report_number) + (f' — Revision {report.revision}' if report.revision else '')
    refs = [['Our Reference', report.our_reference, 'Report No.', number],
            ['Your Reference', report.your_reference, 'Report Date', report.report_date.strftime('%d-%m-%Y') if report.report_date else ''],
            ['Unique Ref. ID', report.unique_reference, 'OMEN ID', report.omen_id]]
    story.append(grid([[Paragraph(f'<b>{t(a)}</b>', SMALL), Paragraph(t(b), SMALL), Paragraph(f'<b>{t(c)}</b>', SMALL),
                        Paragraph(str(d) if c == 'Report No.' else t(d), SMALL)] for a, b, c, d in refs],
                      [full * .18, full * .32, full * .18, full * .32]))
    story.append(Spacer(1, 8))
    if bank_client and report.bank_id:
        branch = report.branch
        to = [report.bank.name, branch.name if branch else '', branch.address if branch else '',
              ', '.join(x for x in ((branch.district if branch else ''), (branch.state if branch else '')) if x)]
    else:
        to = [office.name, office.address, ', '.join(x for x in (office.district, office.state) if x)]
    story += [Paragraph('To,', BODY)] + [Paragraph(t(x), BODY) for x in to if x]
    story += [Spacer(1, 6), Paragraph(f'<b>Subject:</b> Valuation of property of {t(case.borrower.name if case.borrower_id else "")} '
                                      f'— {t(case.service.name)}{" (" + t(case.subtype.name) + ")" if case.subtype else ""}', BODY)]

    answers = {}
    for a in m.ValuationAnswer.objects.filter(valuation=valuation).order_by('answer_group', 'id'):
        answers.setdefault(a.question_id, []).append(a)
    story += body_flowables(template, answers, full)

    story += [Spacer(1, 10), Paragraph(
        'As a result of my appraisal and analysis, it is my considered opinion that the present <b>Fair Market Value</b> '
        f'of the above property in the prevailing condition with aforesaid specifications is {t(stated(report.market_fair_amount))}; '
        f'the <b>Realisable Value</b> of the above property is {t(stated(report.realisable_value_amount))}; '
        f'the <b>Book Value</b> of the above property is {t(stated(report.book_value_amount))}; '
        f'and the <b>Distress Value</b> is {t(stated(report.distress_value_amount))}.', BODY)]
    story.append(KeepTogether([Spacer(1, 8), Paragraph('Place : Bhopal', BODY),
                               Paragraph(f'Date : {report.report_date.strftime("%d-%m-%Y") if report.report_date else ""}', BODY),
                               Spacer(1, 18), Paragraph('(Approved Valuer)', BODY), Paragraph('Official Seal :', BODY),
                               Paragraph('Signature :', BODY)]))
    story.append(KeepTogether([Spacer(1, 12), Paragraph(
        'The undersigned has inspected the property detailed in the Valuation Report dated_____________ on '
        '_____________. We are satisfied that the fair and reasonable market value of the property is '
        'Rs. _________ (Rupees ________________ only).', BODY), Spacer(1, 6),
        Paragraph('Place :', BODY), Paragraph('Date :', BODY), Spacer(1, 18), Paragraph('(Branch Manager)', BODY),
        Paragraph('Name :', BODY), Paragraph('Official Seal :', BODY), Paragraph('Signature :', BODY)]))
    story += [Spacer(1, 10), Paragraph('<b>Encl:</b>', BODY),
              Paragraph('1. Declaration-cum-undertaking from the valuer (Annexure-IV)', BODY),
              Paragraph('2. Model code of conduct for valuer (Annexure V)', BODY)]

    photos = photo_flowables(valuation, full)
    if photos:
        story += [PageBreak(), Paragraph('Photographs', HEAD)] + photos
    if (report.bank_certificate or '').strip():
        story += [Spacer(1, 10), Paragraph('Certificate', HEAD), Paragraph(t(report.bank_certificate), BODY)]
    story.append(PageBreak())
    for title, items in STANDING:
        story.append(Paragraph(f'<u><b>{t(title)}</b></u>', HEAD))
        # reportlab writes the bullet as WinAnsi code 0o177, which the PDF
        # specification renders as a bullet; text extractors report it as \x7f.
        story += [Paragraph(item, BULLET, bulletText='\u2022') for item in items]

    buffer = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.drawString(17 * mm, 10 * mm, f'{valuation.report_number}{" Rev " + str(report.revision) if report.revision else ""}')
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f'Page {doc.page}')
        canvas.restoreState()

    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=15 * mm,
                      bottomMargin=16 * mm, title=f'Valuation Report {valuation.report_number}',
                      author='Omen Assessors').build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
