from django.urls import path
import apps.workorders.services as endpoint_0

urlpatterns = [
    path('api/work-orders/', endpoint_0.create_work_order),
    path('api/work-orders/<uuid:pk>/', endpoint_0.work_order_detail),
    path('api/work-orders/<uuid:pk>/document/', endpoint_0.work_order_document),
    path('api/work-orders/leads/<uuid:pk>/', endpoint_0.lead_work_orders),
]
