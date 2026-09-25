"""Which role grants count. One definition, shared by provisioning and access scope.

A grant qualifies only when it is active in the LEAD project and names a real,
enabled role that belongs to that same project. Provisioning and the valuation
access scope previously each carried their own version of this rule; the scope's
version ignored the role's own status and project, and read an empty set of
grants as unrestricted access (review finding G7).
"""
from django.db.models import F

from .models import RoleAssignment

LEAD_PROJECT = 'LEAD'


def eligible_lead_grants():
    return (RoleAssignment.objects
            .filter(project__name=LEAD_PROJECT, legacy_status='1', legacy_deleted='0',
                    role__isnull=False, role__legacy_deleted='0', role__legacy_status='1')
            .exclude(role__project_id=None)
            .filter(role__project_id=F('project_id')))
