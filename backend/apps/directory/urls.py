from django.urls import path
import apps.directory.services as endpoint_0
import apps.directory.api as endpoint_1

urlpatterns = [
    path('api/intake/offices/', endpoint_0.offices),
    path('api/intake/offices/<uuid:pk>/', endpoint_0.offices),
    path('api/intake/contacts/', endpoint_0.contacts),
    path('api/intake/contacts/<uuid:pk>/', endpoint_0.contacts),
    path('api/offices/', endpoint_1.offices),
]
