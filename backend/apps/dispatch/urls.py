from django.urls import path

import apps.dispatch.services as endpoint_0

urlpatterns = [
    path('api/dispatch/', endpoint_0.dispatches),
    path('api/dispatch/awaiting/', endpoint_0.awaiting),
    path('api/dispatch/reports/<uuid:pk>/', endpoint_0.history),
    path('api/dispatch/<uuid:pk>/', endpoint_0.detail),
    path('api/dispatch/<uuid:pk>/advance/', endpoint_0.advance),
    path('api/dispatch/<uuid:pk>/cancel/', endpoint_0.cancel),
]
