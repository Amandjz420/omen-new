"""Present stable-label models by business domain without changing permissions."""
from django.contrib.admin import AdminSite
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.http import Http404
from django.urls import path, reverse


DOMAINS = {
    'accounts': 'Accounts and roles',
    'organization': 'Employees and organization',
    'directory': 'Banks, clients and contacts',
    'catalog': 'Services and reference data',
    'leads': 'Lead management',
    'workorders': 'Work orders',
    'valuations': 'Valuations and verification',
    'reports': 'Bank reports and approval',
    'billing': 'Billing and collections',
    'documents': 'Documents and storage',
    'dispatch': 'Dispatch and notifications',
    'migration_pipeline': 'Migration and reconciliation',
    'audit': 'Audit and system records',
}


class DomainAutocompleteView(AutocompleteJsonView):
    def serialize_result(self, obj, to_field_name):
        result = super().serialize_result(obj, to_field_name)
        if obj._meta.app_label == 'target_core':
            values = []
            for column in self.model_admin.get_list_display(self.request)[:2]:
                value = column(obj) if callable(column) else getattr(obj, column, None)
                if value is not None and str(value).strip() and str(value) not in values:
                    values.append(str(value))
            result['text'] = ' · '.join(values) if values else obj._meta.verbose_name
            result['text'] += f' [{str(obj.pk)[:8]}]'
        return result


class DomainAdminSite(AdminSite):
    def autocomplete_view(self, request):
        return DomainAutocompleteView.as_view(admin_site=self)(request)

    def get_urls(self):
        return [
            path('domains/<slug:domain>/', self.admin_view(self.domain_index), name='domain_index'),
        ] + super().get_urls()

    def domain_index(self, request, domain):
        if domain not in DOMAINS:
            raise Http404('Unknown business domain')
        return self.app_index(request, f'omen_{domain}')

    def get_app_list(self, request, app_label=None):
        domain_filter = None
        if app_label and app_label.startswith('omen_'):
            domain_filter = app_label.removeprefix('omen_')
            if domain_filter not in DOMAINS:
                return []
            source_label = 'target_core'
        else:
            source_label = app_label

        # Django performs its normal module/model permission filtering first.
        # Group only the visible results; never enumerate models independently.
        original = super().get_app_list(request, source_label)
        grouped, other = {}, []
        for app in original:
            if app['app_label'] != 'target_core':
                other.append(app)
                continue
            leftovers = []
            for entry in app['models']:
                module = entry['model'].__module__.split('.')
                domain = module[1] if len(module) > 2 and module[0] == 'apps' else None
                if domain not in DOMAINS:
                    leftovers.append(entry)
                    continue
                if domain_filter and domain != domain_filter:
                    continue
                if domain not in grouped:
                    grouped[domain] = {
                        'name': DOMAINS[domain], 'app_label': f'omen_{domain}',
                        'app_url': reverse(f'{self.name}:domain_index', kwargs={'domain': domain}),
                        'has_module_perms': True, 'models': [],
                    }
                # Keep Django's existing URLs and add/change/view permissions.
                grouped[domain]['models'].append(entry)
            if leftovers and not domain_filter:
                other.append({**app, 'models': leftovers})
        return [grouped[d] for d in DOMAINS if d in grouped] + other

    def app_index(self, request, app_label, extra_context=None):
        if app_label == 'target_core':
            extra_context = {'title': 'Business domains', **(extra_context or {})}
        return super().app_index(request, app_label, extra_context)
