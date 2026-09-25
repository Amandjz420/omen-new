"""Amounts in words, Indian numbering, exactly as the legacy report prints them.

Ported from NumericToWordConvertorUtility. Units run Hundred, Thousand, Lakh,
Crore, Arab. There is no "Rupees" and no "Only": 3,850,000 is "Thirty Eight Lakh
Fifty Thousand". A fractional part becomes " and <n> Paisa", where a one-digit
fraction is padded (0.5 reads "Fifty Paisa") and a longer one is read whole, as
the legacy code does.
"""
from decimal import Decimal

ONE = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven',
       'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
TEN = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
UNITS = [(10 ** 9, 'Arab'), (10 ** 7, 'Crore'), (10 ** 5, 'Lakh'), (10 ** 3, 'Thousand'), (10 ** 2, 'Hundred')]


def integer_words(n):
    if 0 <= n <= 19:
        return ONE[n]
    if n < 0:
        return 'Minus ' + integer_words(-n)
    for size, name in UNITS:
        if n // size > 0:
            rest = n % size
            return f'{integer_words(n // size)} {name}' + (f' {integer_words(rest)}' if rest else '')
    rest = n % 10
    return TEN[n // 10] + (f' {integer_words(rest)}' if rest else '')


def amount_words(value):
    """Words for an amount; None or empty gives an empty string."""
    if value in (None, ''):
        return ''
    text = format(Decimal(str(value)).normalize(), 'f')
    whole, _, fraction = text.partition('.')
    fraction = fraction.rstrip('0')[:7]
    words = integer_words(int(whole or '0'))
    if fraction and int(fraction) > 0:
        paisa = fraction + '0' if len(fraction) == 1 else fraction
        words += f' and {integer_words(int(paisa))} Paisa'
    return words
