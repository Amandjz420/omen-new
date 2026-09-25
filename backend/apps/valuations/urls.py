from django.urls import path
import apps.valuations.services as endpoint_0
import apps.valuations.submission as endpoint_1
import apps.valuations.files as endpoint_2
import apps.valuations.verification as endpoint_3

urlpatterns = [
    path('api/valuations/', endpoint_0.queue),
    path('api/valuations/cases/<uuid:pk>/', endpoint_0.open_case),
    path('api/valuations/<uuid:pk>/', endpoint_0.detail),
    path('api/valuations/<uuid:pk>/sections/<str:key>/', endpoint_0.section),
    path('api/valuations/<uuid:pk>/submission/', endpoint_1.submission),
    path('api/valuations/<uuid:pk>/photos/', endpoint_2.photos),
    path('api/valuations/<uuid:pk>/photos/<uuid:photo_pk>/', endpoint_2.photo),
    path('api/valuations/<uuid:pk>/photos/<uuid:photo_pk>/file/', endpoint_2.photo_file),
    path('api/valuations/<uuid:pk>/documents/', endpoint_2.answer_document),
    path('api/valuations/<uuid:pk>/documents/<uuid:document_pk>/file/', endpoint_2.document_file),
    path('api/verifications/', endpoint_3.queue),
    path('api/verifications/<uuid:pk>/', endpoint_3.detail),
    path('api/verifications/<uuid:pk>/revert/', endpoint_3.revert),
    path('api/verifications/<uuid:pk>/<str:track>/', endpoint_3.verify),
]
