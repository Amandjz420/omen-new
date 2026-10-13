from django.urls import path
import apps.billing.valuation as endpoint_0
import apps.billing.services as endpoint_1
from apps.billing import receipts as receipt_endpoints

urlpatterns = [
    path('api/valuations/<uuid:pk>/billing/', endpoint_0.billing),
    path('api/receipts/', receipt_endpoints.receipts),
    path('api/receipts/<uuid:pk>/', receipt_endpoints.receipt),
    path('api/receipts/<uuid:pk>/check/', receipt_endpoints.check),
    path('api/receipts/<uuid:pk>/verify/', receipt_endpoints.verify),
    path('api/receipts/<uuid:pk>/void/', receipt_endpoints.void),
    path('api/receipts/<uuid:pk>/document/', receipt_endpoints.document),
    path('api/invoices/', endpoint_1.queue),
    path('api/invoices/valuations/<uuid:pk>/', endpoint_1.for_valuation),
    path('api/invoices/credit-notes/<uuid:pk>/document/', endpoint_1.credit_document),
    path('api/invoices/<uuid:pk>/', endpoint_1.detail),
    path('api/invoices/<uuid:pk>/document/', endpoint_1.document),
    path('api/invoices/<uuid:pk>/payments/', endpoint_1.payment),
    path('api/invoices/<uuid:pk>/write-off/', endpoint_1.write_off),
    path('api/invoices/<uuid:pk>/follow-ups/', endpoint_1.follow_ups),
    path('api/invoices/<uuid:pk>/credit-note/', endpoint_1.credit_note),
]
