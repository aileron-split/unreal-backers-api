"""api_server URL Configuration
"""
from django.conf import settings
# from django.conf.urls.static import static
from django.contrib import admin
# from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('game.urls')),
    path('patreon/', include('patreon_auth.urls')),
    path('config/', include('config.urls')),
]
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# urlpatterns += staticfiles_urlpatterns()
