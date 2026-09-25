"""organization model definitions; legacy database identity is retained."""
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from apps.common.models import Entity, NamedEntity


class Employee(NamedEntity):
    employee_code = models.CharField(max_length=100, blank=True, db_index=True)
    legacy_status = models.CharField(max_length=40, blank=True)
    # HR identity only. Login provisioning is a separate reviewed process.
    # The account this employee signs in with, if any. An employee may have no
    # login and still hold historical assignments; an account may exist with no
    # employee. Set only by provisioning, never by the data importer.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.PROTECT, related_name='employee_profile')

    class Meta:
        app_label = "target_core"


class SalaryBaseline(Entity):
    employee = models.ForeignKey('target_core.Employee', on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    source_variant = models.CharField(max_length=80)

    class Meta:
        app_label = "target_core"


class SalaryBaselineComponent(Entity):
    baseline = models.ForeignKey('target_core.SalaryBaseline', on_delete=models.PROTECT)
    pay_code = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    from_period = models.CharField(max_length=20, blank=True)
    to_period = models.CharField(max_length=20, blank=True)
    mode = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class SalaryResult(Entity):
    employee = models.ForeignKey('target_core.Employee', on_delete=models.PROTECT)
    period = models.CharField(max_length=20)
    gross_earning = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    gross_deduction = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    net_salary = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    paid_days = models.DecimalField(max_digits=8, decimal_places=3, null=True)
    legacy_payment_status = models.CharField(max_length=80, blank=True)

    class Meta:
        app_label = "target_core"


class LeaveOpeningBalance(Entity):
    employee = models.ForeignKey('target_core.Employee', on_delete=models.PROTECT)
    leave_type_code = models.CharField(max_length=80)
    as_of_date = models.DateField()
    days = models.DecimalField(max_digits=10, decimal_places=3)
    evidence = models.JSONField(default=dict)
    reconciled = models.BooleanField(default=False)
    class Meta:
        app_label = "target_core"
        constraints = [models.UniqueConstraint(fields=['employee','leave_type_code','as_of_date'], name='leave_opening_balance_unique')]


class LeadDivision(NamedEntity):
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class LeadSubdivision(NamedEntity):
    division = models.ForeignKey('target_core.LeadDivision', null=True, on_delete=models.PROTECT)
    legacy_status = models.CharField(max_length=40, blank=True)
    legacy_deleted = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class EmployeeTarget(Entity):
    employee = models.ForeignKey('target_core.Employee', on_delete=models.PROTECT)
    financial_year = models.CharField(max_length=20, blank=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    target_cases = models.PositiveIntegerField(null=True)
    target_amount = models.DecimalField(max_digits=24, decimal_places=6, null=True)
    legacy_status = models.CharField(max_length=40, blank=True)

    class Meta:
        app_label = "target_core"


class EmployeeAssignmentRule(Entity):
    employee = models.ForeignKey('target_core.Employee', null=True, on_delete=models.PROTECT)
    client_type = models.ForeignKey('target_core.ClientType', null=True, on_delete=models.PROTECT)
    service = models.ForeignKey('target_core.ServiceType', null=True, on_delete=models.PROTECT)
    subtype = models.ForeignKey('target_core.ServiceSubtype', null=True, on_delete=models.PROTECT)
    report_usage = models.ForeignKey('ReportUsage', null=True, on_delete=models.PROTECT)
    usage_of_report_code = models.CharField(max_length=40, blank=True)
    asset_value = models.DecimalField(max_digits=24, decimal_places=6, null=True)

    class Meta:
        app_label = "target_core"


__all__ = ['Employee', 'SalaryBaseline', 'SalaryBaselineComponent', 'SalaryResult', 'LeaveOpeningBalance', 'LeadDivision', 'LeadSubdivision', 'EmployeeTarget', 'EmployeeAssignmentRule']
