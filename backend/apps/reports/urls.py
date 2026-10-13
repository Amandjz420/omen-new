from django.urls import path
import apps.reports.approvals as endpoint_0
import apps.reports.services as endpoint_1

urlpatterns = [
    path('api/approvals/', endpoint_0.queue),
    path('api/approvals/<uuid:pk>/', endpoint_0.detail),
    path('api/approvals/<uuid:pk>/approve/', endpoint_0.approve),
    path('api/approvals/<uuid:pk>/revert/', endpoint_0.final_revert),
    path('api/valuations/<uuid:pk>/standing/', endpoint_0.standing_detail),
    path('api/valuations/<uuid:pk>/standing/<str:action>/', endpoint_0.standing),
    path('api/bank-reports/', endpoint_1.queue),
    path('api/bank-reports/banks/', endpoint_1.banks),
    path('api/bank-reports/branches/', endpoint_1.branches),
    path('api/bank-reports/<uuid:pk>/', endpoint_1.report),
    path('api/bank-reports/<uuid:pk>/document/', endpoint_1.document),
    path('api/bank-reports/<uuid:pk>/liable/', endpoint_1.change_liable),
]
