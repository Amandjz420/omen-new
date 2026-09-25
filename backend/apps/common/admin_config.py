from django.contrib.admin.apps import AdminConfig


class DomainAdminConfig(AdminConfig):
    default_site = 'apps.common.admin_site.DomainAdminSite'
