from django.urls import path
import apps.leads.services as endpoint_0
import apps.leads.api as endpoint_1
import apps.leads.stages as endpoint_2

urlpatterns = [
    path('api/intake/leads/', endpoint_0.create_lead),
    path('api/intake/leads/<uuid:pk>/', endpoint_0.lead_detail),
    path('api/intake/leads/<uuid:pk>/<str:kind>/', endpoint_0.lead_children),
    path('api/leads/', endpoint_1.leads),
    path('api/leads/<uuid:pk>/', endpoint_1.lead_detail),
    path('api/leads/<uuid:pk>/stages/', endpoint_2.lead_stages),
]
