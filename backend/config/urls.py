from django.contrib import admin
from django.urls import path
from target_core import views, intake
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/intake/catalog/', intake.catalog),
    path('api/intake/offices/', intake.offices),
    path('api/intake/offices/<uuid:pk>/', intake.offices),
    path('api/intake/contacts/', intake.contacts),
    path('api/intake/contacts/<uuid:pk>/', intake.contacts),
    path('api/intake/leads/', intake.create_lead),
    path('api/intake/leads/<uuid:pk>/', intake.lead_detail),
    path('api/intake/leads/<uuid:pk>/<str:kind>/', intake.lead_children),
    path('api/session/', views.session), path('api/login/', views.sign_in), path('api/logout/', views.sign_out), path('api/password/', views.change_password),
    path('api/offices/', views.offices), path('api/leads/', views.leads), path('api/leads/<uuid:pk>/', views.lead_detail),
    path('api/summary/', views.summary),
]
