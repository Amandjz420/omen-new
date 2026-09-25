"""catalog model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class ServiceType(NamedEntity):
    pass

    class Meta:
        app_label = "target_core"


class ServiceSubtype(NamedEntity):
    service = models.ForeignKey('target_core.ServiceType', on_delete=models.PROTECT)

    class Meta:
        app_label = "target_core"


class State(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class District(NamedEntity):
    state = models.ForeignKey('target_core.State', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Region(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Circle(NamedEntity):
    region = models.ForeignKey('target_core.Region', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Block(NamedEntity):
    district = models.ForeignKey('target_core.District', null=True, on_delete=models.PROTECT)
    region = models.ForeignKey('target_core.Region', null=True, on_delete=models.PROTECT)
    circle = models.ForeignKey('target_core.Circle', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    area_type = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Panchayat(NamedEntity):
    block = models.ForeignKey('target_core.Block', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Village(NamedEntity):
    # uam_user.village.PANCHAYAT_ID is a 4-character local code ('0117'), not a
    # key into panchayat.panchayat_id (an 8-digit composite). No row joins, so
    # the raw code is preserved and the relationship is left unasserted.
    panchayat = models.ForeignKey('target_core.Panchayat', null=True, on_delete=models.PROTECT)
    legacy_panchayat_code = models.CharField(max_length=10, blank=True, db_index=True)
    name_hindi = models.CharField(max_length=250, blank=True)
    census_code = models.CharField(max_length=10, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    area_type = models.CharField(max_length=10, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class City(NamedEntity):
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class Location(NamedEntity):
    city = models.ForeignKey('target_core.City', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class SubLocation(NamedEntity):
    location = models.ForeignKey('target_core.Location', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    code = models.CharField(max_length=20, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class AdministrativeDivision(NamedEntity):
    """uam_user.division. Distinct from the lead-management division master."""
    circle = models.ForeignKey('target_core.Circle', null=True, on_delete=models.PROTECT)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class OfficialLocation(NamedEntity):
    city = models.ForeignKey('target_core.City', null=True, on_delete=models.PROTECT)
    kind = models.CharField(max_length=20, blank=True)
    code = models.CharField(max_length=10, blank=True)
    name_hindi = models.CharField(max_length=250, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class IfscArea(Entity):
    """lead_mngt.ifsc has no primary key; the IFSC string is its natural key."""
    ifsc = models.CharField(max_length=45, db_index=True)
    state = models.ForeignKey('target_core.State', null=True, on_delete=models.PROTECT)
    district = models.ForeignKey('target_core.District', null=True, on_delete=models.PROTECT)
    block = models.ForeignKey('target_core.Block', null=True, on_delete=models.PROTECT)

    class Meta:
        app_label = "target_core"


class ScrutinyRequirement(NamedEntity):
    service = models.ForeignKey('target_core.ServiceType', null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class ReportUsage(NamedEntity):
    """lead_mngt.usage_of_reports: why a valuation report was commissioned
    ("To give fresh loan"), scoped by service and subtype. Several tables store
    this id as a bare code; those codes are meaningless without this lookup."""
    service = models.ForeignKey('target_core.ServiceType', null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


__all__ = ['ServiceType', 'ServiceSubtype', 'State', 'District', 'Region', 'Circle', 'Block', 'Panchayat', 'Village', 'City', 'Location', 'SubLocation', 'AdministrativeDivision', 'OfficialLocation', 'IfscArea', 'ScrutinyRequirement', 'ReportUsage']
