from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.directory.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.leads.urls")),
    path("", include("apps.workorders.urls")),
    path("", include("apps.valuations.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.analytics.urls")),
]
