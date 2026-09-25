"""Shared audit recording and ownership transfer on local edits."""
import json
from django.forms.models import model_to_dict
from . import models as m

def snapshot(obj):
    return json.loads(json.dumps(model_to_dict(obj), default=str))


def record(actor, obj, before=None, action='create'):
    m.IntakeAudit.objects.create(actor=actor, action=action, target_model=obj._meta.label,
                                 target_id=obj.pk, before=before or {}, after=snapshot(obj))
    if before is not None:
        m.LocalRecord.objects.get_or_create(target_model=obj._meta.label, target_id=obj.pk)

