from django.urls import path
import apps.valuations.services as endpoint_0
import apps.valuations.submission as endpoint_1
import apps.valuations.files as endpoint_2
import apps.valuations.verification as endpoint_3

import apps.valuations.assist as assist_endpoints
from apps.valuations import checklist as checklist_endpoints

urlpatterns = [
    path('api/valuations/', endpoint_0.queue),
    path('api/valuations/cases/<uuid:pk>/', endpoint_0.open_case),
    path('api/valuations/<uuid:pk>/', endpoint_0.detail),
    path('api/valuations/<uuid:pk>/sections/<str:key>/', endpoint_0.section),
    path('api/valuations/<uuid:pk>/assist/', assist_endpoints.overview),
    path('api/valuations/<uuid:pk>/checklist/', checklist_endpoints.checklist),
    path('api/valuations/<uuid:pk>/checklist/follow-up/', checklist_endpoints.follow_up),
    path('api/valuations/<uuid:pk>/assist/recordings/', assist_endpoints.recording),
    path('api/valuations/<uuid:pk>/assist/documents/', assist_endpoints.document),
    path('api/valuations/<uuid:pk>/assist/sources/<uuid:sid>/retry/', assist_endpoints.retry),
    path('api/valuations/<uuid:pk>/assist/sources/<uuid:sid>/files/<uuid:document_pk>/', assist_endpoints.source_file),
    path('api/valuations/<uuid:pk>/assist/suggestions/<uuid:spk>/accept/', assist_endpoints.accept),
    path('api/valuations/<uuid:pk>/assist/suggestions/<uuid:spk>/dismiss/', assist_endpoints.dismiss),
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
