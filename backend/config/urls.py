from django.urls import path
from target_core import views
urlpatterns = [
    path('api/session/', views.session), path('api/login/', views.sign_in), path('api/logout/', views.sign_out), path('api/password/', views.change_password),
    path('api/offices/', views.offices), path('api/leads/', views.leads), path('api/leads/<uuid:pk>/', views.lead_detail),
    path('api/summary/', views.summary),
]
