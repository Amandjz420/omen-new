"""Database-backed allocation of document numbers.

The legacy allocators read MAX(suffix) and write MAX+1 with no lock, so two
concurrent requests take the same number: 241 leads and 44 dispatches share one.
Here the counter row is locked with SELECT ... FOR UPDATE for the life of the
enclosing transaction, so concurrent allocations serialise instead of colliding.

The counter is seeded from the highest existing number once, and that seed is
computed in SQL rather than by loading every number into Python.
"""
from django.db import transaction
from django.db.models import BigIntegerField, Max
from django.db.models.functions import Cast, Substr

from . import models as m


def legacy_maximum(model, field, prefix):
    """Highest numeric suffix of numbers shaped PREFIX-MMYYDD<counter>.

    The legacy SQL is SUBSTRING(no, 9): two prefix characters, a hyphen and six
    date digits come first. Numbers not in that shape are ignored.
    """
    top = (model.objects.filter(**{f'{field}__regex': rf'^{prefix}-[0-9]{{7,}}$'})
           .annotate(suffix=Cast(Substr(field, 9), BigIntegerField()))
           .aggregate(top=Max('suffix')))['top']
    return top or 0


def allocate(name, model, field, prefix):
    """Next value of the named counter. Must run inside a transaction: the row
    lock that makes this safe is released when that transaction ends."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('allocate() must run inside a transaction so the counter lock is held')
    counter, created = (m.LeadCounter.objects.select_for_update()
                        .get_or_create(name=name, defaults={'value': 0}))
    if created or counter.value == 0:
        counter.value = legacy_maximum(model, field, prefix)
    counter.value += 1
    counter.save(update_fields=['value'])
    return counter.value


def format_number(prefix, day, value):
    """Legacy format: PREFIX-MMYYDD then the counter padded to at least 4 digits."""
    return f'{prefix}-{day:%m%y%d}{value:04d}'
