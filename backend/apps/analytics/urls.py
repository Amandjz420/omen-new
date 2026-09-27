from django.urls import path
import apps.analytics.api as endpoint_0
import apps.analytics.mis as endpoint_1

urlpatterns = [
    path('api/summary/', endpoint_0.summary),
    path('api/mis/', endpoint_1.catalogue),
    path('api/mis/<str:key>/', endpoint_1.result),
    path('api/mis/<str:key>/export/', endpoint_1.export),
]
