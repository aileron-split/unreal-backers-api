from django.conf import settings
from django.contrib import admin
from django.urls import reverse

from patreon_auth.admin import fetch_patreon_info
from .models import APIVariable, GameVersion, GameTier, ServerVariable


@admin.register(GameVersion)
class GameVersionAdmin(admin.ModelAdmin):
    list_display = ('version', 'version_hash', 'note', 'datetime')
    list_display_links = ('version', 'version_hash',)

    search_fields = ('version', 'note',)
    date_hierarchy = 'datetime'

    fields = ('version', 'version_hash', 'public_key', 'note', 'datetime',)

    readonly_fields = ('version_hash', 'public_key')


@admin.register(GameTier)
class GameTierAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tier_code', 'tier_label')
    list_display_links = ('__str__',)
    list_editable = ('tier_code', 'tier_label')

    fields = ('tier_code', 'tier_label')


@admin.register(APIVariable)
class APIVariableAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    list_editable = ('value',)

    search_fields = ('key', 'value')

    readonly_fields = ('tooltip',)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        info = fetch_patreon_info(request)
        extra_context['patreon_info'] = info

        host_address = settings.CSRF_TRUSTED_ORIGINS[0] if settings.CSRF_TRUSTED_ORIGINS else 'http://localhost'
        extra_context['patreon_redirect_uri'] = host_address + reverse('patreon_authorize')

        return super(APIVariableAdmin, self).changelist_view(
            request, extra_context=extra_context
        )


@admin.register(ServerVariable)
class ServerVariableAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    list_editable = ('value',)

    search_fields = ('key', 'value')

    readonly_fields = ('tooltip',)
