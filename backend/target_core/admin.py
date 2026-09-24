"""Admin registration for the target models.

Two things this has to get right, because the admin is a second door onto the
same data as the intake API:

1. Editing an imported record here must transfer ownership exactly as the intake
   API does, or the next legacy import silently overwrites the edit.
2. Migration evidence is never editable. SourceRow, identities, issues, batches
   and the frozen legacy identity are the record of what the source contained;
   an admin edit would destroy the thing they exist to prove.
"""
from django.apps import apps
from django.contrib import admin

from . import models as m

# Evidence and machinery: visible, searchable, never editable.
READ_ONLY = {
    'SourceRow', 'SourceIdentity', 'MigrationIssue', 'ImportBatch', 'IntakeAudit',
    'LocalRecord', 'LeadCounter', 'LegacyAccount', 'LegacyProject', 'RoleDefinition',
    'RoleAssignment', 'LoginEvent',
}
PREFERRED_COLUMNS = ('number', 'name', 'login_id', 'report_number', 'table', 'action', 'created_at')


class EvidenceAdmin(admin.ModelAdmin):
    """Browsable, never writable."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OwnedAdmin(admin.ModelAdmin):
    """Editing an imported record claims it for the application."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            return
        label = obj._meta.label
        imported = m.SourceIdentity.objects.filter(target_model=label, target_id=obj.pk).exists()
        if imported:
            m.LocalRecord.objects.get_or_create(target_model=label, target_id=obj.pk)
        m.IntakeAudit.objects.create(
            actor=request.user, action='admin_edit', target_model=label, target_id=obj.pk,
            before={}, after={field: str(form.cleaned_data[field]) for field in form.changed_data})

    def has_delete_permission(self, request, obj=None):
        # Deleting an imported row would strand its source identity.
        return False


def columns(model):
    names = {f.name for f in model._meta.concrete_fields}
    chosen = [c for c in PREFERRED_COLUMNS if c in names]
    return chosen or ['id']


for model in apps.get_app_config('target_core').get_models():
    if model._meta.proxy or admin.site.is_registered(model):
        continue
    base = EvidenceAdmin if model.__name__ in READ_ONLY else OwnedAdmin
    attrs = {'list_display': columns(model), 'list_per_page': 50}
    searchable = [c for c in ('number', 'name', 'login_id') if c in {f.name for f in model._meta.concrete_fields}]
    if searchable:
        attrs['search_fields'] = searchable
    admin.site.register(model, type(f'{model.__name__}Admin', (base,), attrs))

admin.site.site_header = 'OMEN migration target'
admin.site.site_title = 'OMEN target'
admin.site.index_title = 'Migrated data and intake'
