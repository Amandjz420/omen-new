from django.urls import path
import apps.accounts.api as endpoint_0

urlpatterns = [
    path('api/session/', endpoint_0.session),
    path('api/login/', endpoint_0.sign_in),
    path('api/logout/', endpoint_0.sign_out),
    path('api/password/', endpoint_0.change_password),
]
