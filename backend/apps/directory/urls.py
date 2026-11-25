from django.urls import path
import apps.directory.services as endpoint_0
import apps.directory.api as endpoint_1
import apps.directory.tree as tree

urlpatterns = [
    path('api/intake/offices/', endpoint_0.offices),
    path('api/intake/offices/<uuid:pk>/', endpoint_0.offices),
    path('api/intake/contacts/', endpoint_0.contacts),
    path('api/intake/contacts/<uuid:pk>/', endpoint_0.contacts),
    path('api/offices/', endpoint_1.offices),
    path('api/directory/groups/', tree.groups),
    path('api/directory/branches/', tree.branches),
    path('api/directory/clients/', tree.clients),
    path('api/directory/search/', tree.search),
]
