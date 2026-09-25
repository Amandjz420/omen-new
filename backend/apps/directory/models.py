"""directory model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Bank(NamedEntity):
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class BankBranch(NamedEntity):
    bank = models.ForeignKey('target_core.Bank', on_delete=models.PROTECT)
    ifsc = models.CharField(max_length=40, blank=True, db_index=True)
    micr = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=150, blank=True)
    district = models.CharField(max_length=150, blank=True)
    state = models.CharField(max_length=150, blank=True)

    class Meta:
        app_label = "target_core"


class ClientType(NamedEntity):
    pass

    class Meta:
        app_label = "target_core"


class ClientOffice(NamedEntity):
    branch_name = models.CharField(max_length=500, blank=True)
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    bank = models.ForeignKey('target_core.Bank', null=True, on_delete=models.PROTECT)
    directory_branch = models.ForeignKey('target_core.BankBranch', null=True, on_delete=models.PROTECT)
    address = models.TextField(blank=True)
    owner = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT)
    legacy_working_status = models.CharField(max_length=40, blank=True)
    state = models.CharField(max_length=150, blank=True)
    district = models.CharField(max_length=150, blank=True)
    gstin = models.CharField(max_length=200, blank=True)          # printed on invoices billed to the client
    ifsc = models.CharField(max_length=45, blank=True)

    class Meta:
        app_label = "target_core"


class ContactDesignation(NamedEntity):
    pass

    class Meta:
        app_label = "target_core"


class Contact(NamedEntity):
    office = models.ForeignKey('target_core.ClientOffice', on_delete=models.PROTECT)
    designation = models.ForeignKey('target_core.ContactDesignation', null=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=80, blank=True)
    alternate_phone = models.CharField(max_length=80, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Bank', 'BankBranch', 'ClientType', 'ClientOffice', 'ContactDesignation', 'Contact']
