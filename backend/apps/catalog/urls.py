from django.urls import path
from . import api

urlpatterns = [path('api/intake/catalog/', api.catalog)]
