"""Which bank a form belongs to.

A bank's own valuation form is its own service subtype, named with the bank's IFSC
prefix: L & B ( SBIN), L & B ( CNRB), Land ( CNRB ). A client office's bank is the
prefix of its IFSC. Introduced in the legacy system in February and March 2024; its
subtype was a free choice there, and 8 cases since used another bank's form.
"""
import re

FORM_CODE = re.compile(r'\(\s*([A-Z]{4})\s*\)\s*$')
IFSC = re.compile(r'^([A-Z]{4})0[A-Z0-9]{6}$')


def form_bank(subtype):
    """The bank code a subtype's form belongs to, or None for a form for any bank."""
    match = FORM_CODE.search((subtype.name if subtype else '') or '')
    return match.group(1) if match else None


def office_bank(office):
    """The bank code of a client office, from its IFSC; None when it has no valid one."""
    match = IFSC.match(((office.ifsc if office else '') or '').strip().upper())
    return match.group(1) if match else None


def wrong_bank(subtype, office):
    """Why this subtype's form is not for this office's bank; empty if it may be used."""
    form, bank = form_bank(subtype), office_bank(office)
    if form and bank and form != bank:
        return f'{subtype.name.strip()} is the form for {form}; this lead\'s client is {bank}. Choose {bank}\'s form or the general one'
    return ''
