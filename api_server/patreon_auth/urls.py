from django.urls import path

from . import views

urlpatterns = [
    path('register', views.register),
    path('authorize', views.authorize, name='patreon_authorize'),
]
