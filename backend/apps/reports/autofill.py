"""The assessed values a bank report states, read from the valuation's own answers.

Review of October 2026: the bank report form asked for the fair market value (FMV),
the expected realisable value (ERV) and the distress sale value (DSV) by hand,
although the assessor has already entered them on the valuation form, either

  * in a table question, usually "Other Market Value", whose columns are
    FMV / ERV / DSV (or "Fair market value", "Estimated realizable value",
    "Forced/Distress sales value"), or
  * as separate written answers: "Fair Market Value of immovable property",
    "Present Market Value", "Realizable Value of the Property", "Distress Value".

The report form is prefilled from these, and stays editable: the figures are a
starting point, the person generating the report remains responsible for them. A
table is preferred to written answers, and within either, the first question in
form order that yields a figure wins. Values "after completion" are not the
present value, and tables about an earlier valuation ("Was property valued
earlier") are about another one; neither is used.
"""
import re
from decimal import Decimal

from target_core import models as m
from apps.valuations.services import KINDS, form_questions

FIELDS = ('market_fair_amount', 'realisable_value_amount', 'distress_value_amount')
EXCLUDE = re.compile(r'after\s+completion|completion\s+of|negative|other\s+than|book\s+value|guideline|circle|govt|government|insur', re.I)
PATTERNS = {
    'distress_value_amount': re.compile(r'\bdsv\b|distress|forced', re.I),
    'realisable_value_amount': re.compile(r'\berv\b|reali[sz]able', re.I),
    'market_fair_amount': re.compile(r'\bfmv\b|fair\s+market|market\s+value', re.I),
}
# Questions about some other valuation, such as "Was property valued earlier", whose
# table also has a market value column.
OTHER_VALUATION = re.compile(r'earlier|previous|prior|last\s+valu|past', re.I)
NUMBER = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|cr\b)?', re.I)
SCALE = {'lakh': 100000, 'lac': 100000, 'crore': 10000000, 'cr': 10000000}


def field_for(label):
    """Which assessed value a question or column label names, if any."""
    label = ' '.join((label or '').split())
    if not label or EXCLUDE.search(label):
        return None
    for field, pattern in PATTERNS.items():          # distress and realisable before market
        if pattern.search(label):
            return field
    return None


def amount(text):
    """The first figure in an answer: "Rs. 25,00,000/-" -> 2500000, "45.5 lakh" -> 4550000."""
    found = NUMBER.search(str(text or ''))
    if not found:
        return None
    value = Decimal(found.group(1).replace(',', ''))
    unit = (found.group(2) or '').lower().rstrip('s')
    return value * SCALE.get(unit, 1) if unit else value


def from_rows(questions, answers):
    """questions: [(id, text, kind, [(option_id, label)])]; answers: {question_id:
    [(option_id, group, value)]}. Returns ({field: Decimal}, {field: question text})."""
    tables, written = {}, {}
    for qid, text, kind, options in questions:
        given = answers.get(qid) or []
        if OTHER_VALUATION.search(text or ''):
            continue
        if kind in ('grid', 'formula', 'sum'):
            columns = {oid: field_for(label) for oid, label in options}
            if not any(columns.values()):
                continue
            for group in sorted({g for _, g, _ in given}):
                cells = {}
                for oid, g, value in given:
                    field = columns.get(oid)
                    if g == group and field and field not in cells and amount(value) is not None:
                        cells[field] = amount(value)
                for field, value in cells.items():
                    tables.setdefault(field, (value, text))
                if cells:
                    break                                  # the first filled row of the table
        elif kind == 'text':
            field = field_for(text)
            value = next((amount(v) for oid, _, v in given if oid is None and amount(v) is not None), None)
            if field and value is not None:
                written.setdefault(field, (value, text))
    chosen = {f: tables.get(f) or written.get(f) for f in FIELDS}
    return ({f: v[0] for f, v in chosen.items() if v}, {f: v[1] for f, v in chosen.items() if v})


def assessed_values(valuation):
    """{'values': {field: '2500000.00'}, 'sources': {field: question text}}."""
    questions = list(form_questions(valuation).prefetch_related('options'))
    rows = []
    for q in questions:
        kind = KINDS.get(q.answer_type, 'text')
        rows.append((q.pk, q.text.strip(), kind, [(o.pk, o.value) for o in q.options.all()]))
    answers = {}
    for a in m.ValuationAnswer.objects.filter(valuation=valuation).order_by('answer_group', 'id'):
        answers.setdefault(a.question_id, []).append((a.option_id, a.answer_group, a.value))
    values, sources = from_rows(rows, answers)
    return {'values': {f: str(v.quantize(Decimal('0.01'))) for f, v in values.items()}, 'sources': sources}
