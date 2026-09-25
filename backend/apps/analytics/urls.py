from django.urls import path
import apps.analytics.api as endpoint_0

urlpatterns = [
    path('api/summary/', endpoint_0.summary),
]
