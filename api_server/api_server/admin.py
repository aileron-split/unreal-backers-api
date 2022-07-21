from django.contrib.admin import AdminSite


class ServerAdminSite(AdminSite):
    site_title = 'Backers Plugin'
    site_header = 'Backers API Administration'

    index_title = 'API Index'
