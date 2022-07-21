from django.contrib.admin.apps import AdminConfig


class ServerAdminConfig(AdminConfig):
    default_site = 'api_server.admin.ServerAdminSite'
    