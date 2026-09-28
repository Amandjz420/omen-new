"""Admin registration for the target models.

Two things this has to get right, because the admin is a second door onto the
same data as the intake API:

1. Editing an imported record here must transfer ownership exactly as the intake
   API does, or the next legacy import silently overwrites the edit.
2. Migration evidence is never editable. SourceRow, identities, issues, batches
   and the frozen legacy identity are the record of what the source contained;
   an admin edit would destroy the thing they exist to prove.
"""
from django.contrib import admin
from django.db import models as db_models
from django.utils.text import Truncator

from .admin_options import LAYOUTS

from target_core import models as m

# Evidence and machinery: visible, searchable, never editable.
READ_ONLY = {
    'FinancialOperation',
    'SourceRow', 'SourceIdentity', 'MigrationIssue', 'ImportBatch', 'IntakeAudit',
    'LocalRecord', 'LeadCounter', 'LegacyAccount', 'LegacyProject', 'RoleDefinition',
    'RoleAssignment', 'LoginEvent',
}
# Workflow records are changed only through their workflow services, which number,
# validate, audit and lock them. The generic admin bypassed all of that: a lead
# could be saved with no number and no audit entry, and an issued invoice edited
# (review finding G6). They are browsable here but never writable. Reference data
# (catalogue, geography, directory, charge heads, Omen's accounts, employees and
# their assignments, question and report-template setup) stays editable. Records
# kept as historical evidence (dispatch and SMS history, stored-document metadata,
# the retained salary baselines) are view-only too.
WORKFLOW = {
    'Lead', 'RequestedService', 'Borrower', 'Case', 'FollowUp', 'LeadNote', 'LeadParty', 'LeadAttachment',
    'WorkOrder', 'WorkOrderRevision',
    'Valuation', 'ValuationAnswer', 'ValuationAttachment', 'ValuationVerification', 'Reversion', 'ValuationEvent',
    'AssistSource', 'Suggestion',
    'BankReport',
    'ValuationCharge', 'Invoice', 'InvoiceLine', 'CreditNote', 'Receipt', 'ReceiptAllocation', 'InvoiceFollowUp',
    'Dispatch', 'DispatchItem', 'SmsMessage',
    'Document', 'DocumentUsage', 'UploadConfiguration',
    'SalaryBaseline', 'SalaryBaselineComponent', 'SalaryResult', 'LeaveOpeningBalance',
}

STATUS_LABELS = {
    'Lead': {'1': 'New lead', '2': 'In process', '3': 'Cancelled', '4': 'Closed'},
    'Invoice': {'1': 'Fully paid', '2': 'Partly paid'},
}


class SourceSchemaFilter(admin.SimpleListFilter):
    title = 'source schema'
    parameter_name = 'schema'

    def lookups(self, request, model_admin):
        from apps.migration_pipeline.services import SPECS
        return [(s, s) for s in sorted({spec[0] for spec in SPECS})]

    def queryset(self, request, queryset):
        return queryset.filter(schema=self.value()) if self.value() else queryset


class SourceTableFilter(admin.SimpleListFilter):
    title = 'source table'
    parameter_name = 'table'

    def lookups(self, request, model_admin):
        from apps.migration_pipeline.services import SPECS
        schema = request.GET.get('schema')
        return [(t, t) for t in sorted({s[1] for s in SPECS if not schema or s[0] == schema})]

    def queryset(self, request, queryset):
        return queryset.filter(table=self.value()) if self.value() else queryset


def field_at(model, path):
    for name in path.split('__'):
        field = model._meta.get_field(name)
        if field.is_relation:
            model = field.related_model
    return field


def display_column(model, path):
    field = field_at(model, path)
    label = str(field.verbose_name)
    if '__' in path:
        parts = path.split('__')
        label = parts[-2].replace('_', ' ') + ('' if parts[-1] in ('name', 'username') else ' ' + label)
    if path == 'legacy_status':
        label = 'Status (legacy)'

    @admin.display(description=label.capitalize(), ordering=path,
                   boolean=isinstance(field, db_models.BooleanField))
    def column(obj):
        value = obj
        parts = path.split('__')
        for name in parts[:-1]:
            value = getattr(value, name, None)
            if value is None:
                return None
        raw = getattr(value, parts[-1], None)
        if path == 'legacy_status':
            return STATUS_LABELS.get(model.__name__, {}).get(raw, raw)
        if field.choices:
            raw = getattr(value, f'get_{parts[-1]}_display')()
        return Truncator(raw).chars(100) if isinstance(raw, str) else raw

    column.__name__ = 'show_' + path.replace('__', '_')
    return column


class ListAdmin(admin.ModelAdmin):
    related_columns = ()
    list_per_page = 50
    list_max_show_all = 200
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER
    empty_value_display = '—'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Large migration payloads and audit snapshots are available on detail
        # pages, but need not be loaded for every row of a metadata-only list.
        if request.resolver_match and request.resolver_match.url_name.endswith('_changelist'):
            bulky = [f.name for f in self.model._meta.fields if isinstance(f, db_models.JSONField)]
            if bulky:
                queryset = queryset.defer(*bulky)
        return queryset.select_related(*self.related_columns) if self.related_columns else queryset


class EvidenceAdmin(ListAdmin):
    """Browsable, never writable."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class OwnedAdmin(ListAdmin):
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
    return LAYOUTS[model.__name__][0].split()


def register_models(models):
    for model in models:
        if model._meta.proxy or admin.site.is_registered(model):
            continue
        base = EvidenceAdmin if model.__name__ in READ_ONLY | WORKFLOW else OwnedAdmin
        display, search, filters, ordering = LAYOUTS[model.__name__]
        # Fail at startup if a configured column is stale, rather than silently
        # omitting it. Every existing model has an explicitly reviewed layout.
        paths = display.split()
        attrs = {'list_display': [display_column(model, p) for p in paths],
                 'search_fields': search.split(), 'list_filter': filters.split(),
                 'ordering': tuple(ordering.split()),
                 'related_columns': tuple(sorted({p.rsplit('__', 1)[0] for p in paths if '__' in p})),
                 'autocomplete_fields': tuple(f.name for f in model._meta.fields if f.is_relation),
                 'search_help_text': 'Search by ' + ', '.join(p.lstrip('=^@').replace('__', ' / ').replace('_', ' ') for p in search.split()) + '.',
                 'exclude': ('issued_password_hash',) if model.__name__ == 'LegacyAccount' else ()}
        if model.__name__ in ('SourceRow', 'SourceIdentity'):
            attrs['list_filter'] = [SourceSchemaFilter if f == 'schema' else SourceTableFilter if f == 'table' else f
                                    for f in attrs['list_filter']]
        admin.site.register(model, type(f'{model.__name__}Admin', (base,), attrs))
    

admin.site.site_header = 'OMEN administration'
admin.site.site_title = 'OMEN'
admin.site.index_title = 'Business domains'
