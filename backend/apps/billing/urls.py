from django.urls import path
import apps.billing.valuation as endpoint_0
import apps.billing.services as endpoint_1

urlpatterns = [
    path('api/valuations/<uuid:pk>/billing/', endpoint_0.billing),
    path('api/invoices/', endpoint_1.queue),
    path('api/invoices/valuations/<uuid:pk>/', endpoint_1.for_valuation),
    path('api/invoices/credit-notes/<uuid:pk>/document/', endpoint_1.credit_document),
    path('api/invoices/<uuid:pk>/', endpoint_1.detail),
    path('api/invoices/<uuid:pk>/document/', endpoint_1.document),
    path('api/invoices/<uuid:pk>/payments/', endpoint_1.payment),
    path('api/invoices/<uuid:pk>/write-off/', endpoint_1.write_off),
    path('api/invoices/<uuid:pk>/credit-note/', endpoint_1.credit_note),
]
