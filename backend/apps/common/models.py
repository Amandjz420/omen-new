"""Abstract model bases. Persistent labels deliberately remain stable."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        app_label = "target_core"
        abstract = True


class NamedEntity(Entity):
    name = models.CharField(max_length=500)
    class Meta:
        app_label = "target_core"
        abstract = True


