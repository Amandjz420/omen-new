from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from target_core.models import ClientOffice as Office, Contact, Lead, Case, ImportBatch, SourceRow
from apps.accounts.api import staff_api


@require_GET
@staff_api
def summary(request):
    year = request.GET.get('year')
    qs = Case.objects.all()
    if year:
        try:
            year = int(year)
            if not 1900 <= year <= 9998:
                raise ValueError()
            qs = qs.filter(lead__received_date__gte=f'{year}-04-01', lead__received_date__lt=f'{year+1}-04-01')
        except ValueError:
            return JsonResponse({'error': 'year must be the financial-year start, e.g. 2026'}, status=400)
    latest = ImportBatch.objects.filter(status__startswith='completed',conversion_version__startswith='mysql-target').order_by('-created_at').first()
    services=[{'service':r['service__name'],'count':r['count']} for r in qs.values('service__name').annotate(count=Count('id')).order_by('-count')]
    return JsonResponse({'offices': Office.objects.count(), 'leads': Lead.objects.count(), 'contacts': Contact.objects.count(),
                         'cases': qs.count(), 'unlinked_cases': qs.filter(lead__isnull=True).count(),
                         'services': services, 'quarantined_source_rows':SourceRow.objects.filter(outcome='quarantined').count(),
                         'source_rows': SourceRow.objects.count(),
                         'rows_with_issues': SourceRow.objects.exclude(problems=[]).exclude(outcome='quarantined').count(),
                         'policy': 'Imported and locally created cases. Unresolved source rows are quarantined. Imported dates use the lead-entry proxy; local intake records the received date.',
                         'latest_import': {'created_at': latest.created_at, 'summary': latest.summary} if latest else None})

