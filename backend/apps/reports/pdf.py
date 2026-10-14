"""Render the bank report, laid out as the previous system printed it.

Reproduces ValuationBankReportUtil.prepareLeadHTML (bank clients) and
prepareReportHTML (others), the one generator the previous system used for every
bank: what differs between banks is only the template (which questions print),
chosen by client type, bank, service and subtype. The page follows the legacy
report, which banks know:

  * the top of the first page is left blank for the pre-printed letterhead the
    report is printed on (the legacy code: "space for letter head header");
  * our reference, date and the bank's reference at the top right;
  * "Name & Address of Branch" and "Name of Customer (s)/ Borrower unit" as
    labelled rows, then the service and subtype as an underlined title;
  * each report heading as a bordered form: index | question | answer, a table or
    amount question across the full width with its own bordered table;
  * the valuer's guidance paragraph, the opinion stating the four values, the
    valuer's and the branch manager's blocks with room for seal and signature,
    the enclosures, the photographs and the firm's standing text;
  * question labels in a serif face and answers in a sans face; the report
    number at the foot of each page and "n of N" beside it.

Presentation is corrected where the legacy layout was plainly broken: the page is
A4 (the legacy converter, given no size, printed US Letter); amounts print with
Indian digit grouping and read "(Rupees ... only)" around the words instead of
"...Thousand(Rupees only)"; HTML entities no longer print as "&rdquo;"; dates read
dd-mm-yyyy; empty references are left out rather than printed as "null".

The standing text is the firm's own legal wording and is reproduced as written,
including "Sales comparison approach is used for:", which the legacy report
prints with nothing after it.

Every value is escaped, since templates and answers are free text.
"""
import io
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from apps.documents.storage import read_bytes
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from target_core import models as m
from apps.valuations.services import KINDS, LIVE, answer_of, number, options_of
from apps.common.words import amount_words

FIRM = ['Omen Assessors', 'F-6, 1st Floor, Sanchi Complex, Opposite Board Office, Shivaji Nagar, Bhopal (M.P.) 462016']
# The letterhead the legacy report linked to at
# http://omenassessors.com/resources/UAM/img/header_img.png, which now returns 404
# on .com and .in alike. The file survives in the legacy source (header_img.png,
# 590 x 206, identical in the Lead, UAM and Payroll apps) and is bundled here, so
# reports no longer depend on the website.
LETTERHEAD = Path(__file__).resolve().parent / 'assets' / 'letterhead.png'
PHOTO_LABELS = {1: 'Front', 2: 'Inside', 3: 'Right View', 4: 'Left View', 5: 'Location Plan', 6: 'Site Plan', 7: 'Other'}

# The legacy report's faces: question labels and running text in Times (its "serif"
# class, and the face its "arial" body fell back to), answers in Helvetica (its
# "sansserif" class).
SERIF = ParagraphStyle('serif', fontName='Times-Roman', fontSize=9.5, leading=12)
SERIF_BOLD = ParagraphStyle('serif-bold', parent=SERIF, fontName='Times-Bold')
SANS = ParagraphStyle('sans', fontName='Helvetica', fontSize=8.5, leading=11)
REFS = ParagraphStyle('refs', parent=SERIF, fontSize=8, leading=10, alignment=TA_RIGHT)
TITLE = ParagraphStyle('title', parent=SERIF, fontSize=10.5, alignment=TA_CENTER)
RIGHT = ParagraphStyle('right', parent=SERIF, alignment=TA_RIGHT)
HEAD = ParagraphStyle('head', parent=SERIF_BOLD, spaceBefore=8, spaceAfter=3)
BULLET = ParagraphStyle('bullet', parent=SERIF, leftIndent=12, bulletIndent=2)
CAPTION = ParagraphStyle('caption', parent=SANS, fontSize=8, alignment=TA_CENTER)
# Bordered like the legacy ".data td" cells: half-point rules, 10px by 5px padding.
FORM = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
PLAIN = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
         ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
GUIDANCE = ('(Valuation: Here the approved valuer should discuss in detail his approach (Market Approach, Income '
            'Approach and Cost Approach) to valuation of property and indicate how the value has been arrived at, '
            'supported by necessary calculations. Also, such aspects as i) Saleability ii) Likely rental values in '
            'future in iii) Any likely income it may generate, may be discussed).')
LETTERHEAD_SPACE = 38 * mm      # the pre-printed letterhead's depth on the first page

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
    """A bordered table of answers, as the legacy "multidata" tables: every cell ruled."""
    table = Table([[c if not isinstance(c, str) else Paragraph(t(c), SANS) for c in r] for r in rows],
                  colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(FORM))
    return table


def template_lines(template):
    """The lines a report prints. As in the legacy queries, a line prints only
    under a live heading and with a live question; lines with no heading or no
    question never appeared in a legacy report."""
    return (m.ReportTemplateLine.objects.filter(template=template, question__isnull=False,
                                                question__legacy_deleted__in=LIVE, heading__isnull=False,
                                                heading__legacy_deleted__in=LIVE)
            .select_related('question', 'heading').order_by('heading__display_order', 'heading__name', 'sequence', 'id'))


def body_flowables(template, answers, full):
    """Each report heading as a bordered form, as the legacy "data" tables.

    A simple question is a row: index | question | answer. A table or amount
    question spans the form's width, its answers in a bordered table of their own.
    Legacy nested those tables inside the row; here the form is closed above them
    and reopened below, so a long table can run onto the next page instead of
    being cut off, and the ruled edges still meet."""
    widths = [full * .06, full * .35, full * .59]
    out, rows, spans, current = [], [], [], None

    def close():
        nonlocal rows, spans
        if rows:
            table = Table(rows, colWidths=widths)
            table.setStyle(TableStyle(FORM + spans))
            out.append(table)
        rows, spans = [], []

    def across(*flowables):
        rows.append([list(flowables), '', ''])
        spans.append(('SPAN', (0, len(rows) - 1), (-1, len(rows) - 1)))

    for line in template_lines(template):
        if line.heading_id != current:
            close()
            if current is not None:
                out.append(Spacer(1, 10))
            current = line.heading_id
            across(Paragraph(f'<b>{t(line.heading.name)}</b>', SERIF_BOLD))
        q, given = line.question, answers.get(line.question_id, [])
        kind = KINDS.get(q.answer_type, 'text')
        index, label = t(line.indexing).strip(), t(line.output_label).strip()
        before, after = t(line.content_before).strip(), t(line.content_after).strip()
        options = options_of(q)
        if kind in ('grid', 'formula', 'sum'):
            across(*([Paragraph(f'{index} {label}'.strip(), SERIF)] + ([Paragraph(before, SANS)] if before else [])))
            close()
            value = answer_of(q, given, options)
            if kind == 'sum':
                body = [['Sr.No.', 'Items', 'Amount (Rs. in Lacs)']]
                body += [[str(n), o.value.strip(), (value['values'].get(str(o.pk)) or '0').strip()] for n, o in enumerate(options, 1)]
                body.append(['', 'Total Amount', f"{value['total']:.2f}"])
                out.append(grid(body, [full * .1, full * .6, full * .3]))
            else:
                header = ['Sr'] + [o.value.strip() for o in options]
                body = [[str(r['group'])] + [r['cells'].get(str(o.pk), '') for o in options] for r in value['rows']]
                n = len(header)
                out.append(grid([header] + body, [full * .07] + [full * .93 / (n - 1)] * (n - 1)))
            if after:
                across(Paragraph(after, SANS))
        else:
            values = [t(a.value.strip()) for a in given if (a.value or '').strip()]
            answer = ' '.join(x for x in (before, ', '.join(values), after) if x) if values else ''
            rows.append([Paragraph(index, SERIF), Paragraph(label, SERIF), Paragraph(answer, SANS)])
    close()
    return out


def photo_flowables(valuation, full):
    """The photograph page, as the legacy report: the four views two to a row in
    ruled frames, the location and site plans across the page, each captioned."""
    small, wide, out = [], [], []
    for p in m.ValuationAttachment.objects.filter(valuation=valuation).select_related('document').order_by('attachment_type', 'created_at'):
        code = int(p.attachment_type) if (p.attachment_type or '').isdigit() else None
        caption = Paragraph(f'<b>{t(PHOTO_LABELS.get(code, "Photo"))}</b> {t(p.name)}'.strip(), CAPTION)
        across_page = code in (5, 6)
        width = full - 8 if across_page else full / 2 - 8
        # Photographs stored here and in the previous system's bucket alike; a legacy
        # photo was once a placeholder, so a regenerated report reached the bank
        # without its pictures.
        data, picture = read_bytes(p.document), None
        if data:
            try:
                picture = Image(io.BytesIO(data), width=width, height=width * (.45 if across_page else .62), kind='proportional')
            except Exception:
                picture = None
        cell = [picture or Paragraph('Photograph could not be retrieved', CAPTION), Spacer(1, 3), caption]
        (wide if across_page else small).append(cell)
    for i in range(0, len(small), 2):
        pair = small[i:i + 2] + ([''] if len(small[i:i + 2]) == 1 else [])
        table = Table([pair], colWidths=[full / 2] * 2)
        alone = len(small[i:i + 2]) == 1                    # an odd photo: frame only its own cell
        table.setStyle(TableStyle(([('BOX', (0, 0), (0, 0), 0.5, colors.black)] + FORM[1:]) if alone else FORM))
        out += [table, Spacer(1, 6)]
    for cell in wide:
        table = Table([[cell]], colWidths=[full])
        table.setStyle(TableStyle(FORM))
        out += [table, Spacer(1, 6)]
    return out


def numbered_canvas(report_number):
    """Each page's foot: the report number at the left and "n of N" at the right,
    as the legacy report's running footer; the total is known once all are laid out."""
    class NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self.setFont('Times-Roman', 6.5)
                self.drawString(17 * mm, 10 * mm, report_number)
                self.setFont('Times-Roman', 11)
                self.drawRightString(A4[0] - 17 * mm, 10 * mm, f'{self._pageNumber} of {total}')
                super().showPage()
            super().save()
    return NumberedCanvas


def render(report, template, bank_client):
    valuation, case = report.valuation, report.valuation.case
    office, full = case.lead.office, A4[0] - 34 * mm
    when = report.report_date.strftime('%d-%m-%Y') if report.report_date else ''

    # References at the top right, under the space left for the letterhead. The
    # unique reference and OMEN ID print only when given.
    refs = [('OUR REFERENCE', report.our_reference), ('DATE', when), ('YOUR REFERENCE', report.your_reference)]
    refs += [(label, value) for label, value in (('UNIQUE REF. ID', report.unique_reference), ('OMEN ID', report.omen_id))
             if (value or '').strip()]
    story = [Spacer(1, LETTERHEAD_SPACE), Paragraph('<br/>'.join(f'<b>{label} :</b> {t(value)}' for label, value in refs), REFS),
             Spacer(1, 6)]

    if bank_client and report.bank_id:
        branch = report.branch
        to = [report.bank.name, branch.name if branch else '', branch.address if branch else '',
              '\u00a0\u00a0'.join(x for x in ((branch.district if branch else ''), (branch.state if branch else '')) if x)]
    else:
        to = [office.name, office.address, '\u00a0\u00a0'.join(x for x in (office.district, office.state) if x)]
    borrower = case.borrower.name.strip() if case.borrower_id else ''
    service = case.service.name.strip() if case.service_id else ''
    title = f'{service}- ({case.subtype.name.strip()})' if case.subtype_id else service
    addressed = Table([
        [Paragraph('Name &amp; Address of Branch :', SERIF), Paragraph('<br/>'.join(['To,'] + [t(x) for x in to if (x or '').strip()]), SERIF)],
        [Paragraph('Name of Customer (s)/ Borrower unit :<br/>(for which valuation report is sought):', SERIF), Paragraph(t(borrower), SERIF)],
        [Paragraph(f'<u>{t(title)}</u>', TITLE), ''],
    ], colWidths=[full * .42, full * .58])
    addressed.setStyle(TableStyle(PLAIN + [('SPAN', (0, 2), (1, 2)), ('TOPPADDING', (0, 2), (1, 2), 8)]))
    story += [addressed, Spacer(1, 8)]

    answers = {}
    for a in m.ValuationAnswer.objects.filter(valuation=valuation).order_by('answer_group', 'id'):
        answers.setdefault(a.question_id, []).append(a)
    story += body_flowables(template, answers, full)

    story += [Spacer(1, 14), Paragraph(f'<b>{GUIDANCE}</b>', SERIF), Spacer(1, 8),
              Paragraph('Photograph of owner/representative with property in background to be enclosed.<br/>'
                        'Screen shot of longitude/latitude and co-ordinates of property using GPS/Various Apps/Internet sites', SERIF),
              Spacer(1, 8), Paragraph(
        'As a result of my appraisal and analysis, it is my considered opinion that the present <b>Fair Market Value</b> '
        f'of the above property in the prevailing condition with aforesaid specifications is {t(stated(report.market_fair_amount))}; '
        f'the <b>Realisable Value</b> of the above property is {t(stated(report.realisable_value_amount))}; '
        f'the <b>Book Value</b> of the above property is {t(stated(report.book_value_amount))}; '
        f'and the <b>Distress Value</b> is {t(stated(report.distress_value_amount))}.', SERIF)]

    def signed(left, right):
        table = Table([[left, right]], colWidths=[full * .5, full * .5])
        table.setStyle(TableStyle(PLAIN))
        return table
    valuer = signed(Paragraph(f'Place : Bhopal\u00a0\u00a0\u00a0Date : {when}', SERIF),
                    [Paragraph('(Approved Valuer)', RIGHT), Spacer(1, 12), Paragraph('Official Seal :', RIGHT),
                     Spacer(1, 52), Paragraph('Signature :', RIGHT)])
    story.append(KeepTogether([Spacer(1, 14), valuer]))
    manager = signed(Paragraph('Place :\u00a0\u00a0\u00a0Date :', SERIF),
                     [Paragraph('(Branch Manager)', RIGHT), Paragraph('Name :', RIGHT), Paragraph('Official Seal :', RIGHT),
                      Spacer(1, 40), Paragraph('Signature :', RIGHT)])
    story.append(KeepTogether([Spacer(1, 18), Paragraph(
        'The undersigned has inspected the property detailed in the Valuation Report dated_____________ on '
        '_____________. We are satisfied that the fair and reasonable market value of the property is '
        'Rs. _________ (Rupees ________________ only).', SERIF), Spacer(1, 4), manager]))
    story.append(KeepTogether([Spacer(1, 12), Paragraph('Encl:', SERIF),
                               Paragraph('1. Declaration-cum-undertaking from the valuer (Annexure-IV)', SERIF),
                               Paragraph('2. Model code of conduct for valuer (Annexure V)', SERIF)]))

    photos = photo_flowables(valuation, full)
    if photos:
        story += [PageBreak()] + photos
    if (report.bank_certificate or '').strip():
        story += [Spacer(1, 10), Paragraph('Certificate', HEAD), Paragraph(t(report.bank_certificate), SERIF)]
    story.append(PageBreak())
    for title_text, items in STANDING:
        story.append(Paragraph(f'<u><b>{t(title_text)}</b></u>', HEAD))
        # reportlab writes the bullet as WinAnsi code 0o177, which the PDF
        # specification renders as a bullet; text extractors report it as \x7f.
        story += [Paragraph(item, BULLET, bulletText='\u2022') for item in items]

    buffer = io.BytesIO()
    # A reissued report says so on every page, beside its number.
    number = f'{valuation.report_number}{" Revision " + str(report.revision) if report.revision else ""}'
    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm, topMargin=12 * mm,
                      bottomMargin=18 * mm, title=f'Valuation Report {valuation.report_number}',
                      author='Omen Assessors').build(story, canvasmaker=numbered_canvas(number))
    return buffer.getvalue()
