"""api_server URL Configuration
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('game.urls')),
    path('patreon/', include('patreon_auth.urls')),
    path('config/', include('config.urls')),
]
