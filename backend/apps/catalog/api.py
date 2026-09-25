"""Reference choices used by lead intake."""
from django.http import JsonResponse
from target_core import models as m
from apps.common.http import endpoint

@endpoint(['GET'])
def catalog(request):
    def choices(model, extra=()):
        return list(model.objects.order_by('name', 'id').values('id', 'name', *extra))
    employees = m.Employee.objects.exclude(user__is_active=False).order_by('name').values('id', 'name', 'employee_code')
    return JsonResponse({'services': choices(m.ServiceType), 'subtypes': choices(m.ServiceSubtype, ['service_id']),
                         'employees': list(employees), 'client_types': choices(m.ClientType),
                         'designations': choices(m.ContactDesignation), 'banks': choices(m.Bank)})

