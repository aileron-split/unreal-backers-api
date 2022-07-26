import importlib

from django.conf import settings
from django.contrib import admin
from django.urls import reverse

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
        extra_context['config_extra'] = template_extra_info(request) or {}

        for platform in settings.BACKER_PLATFORMS:
            platform_admin = importlib.import_module(f'{platform}_auth.admin')
            extra_context[f'{platform}_info'] = f'{platform}_auth.admin'
            try:
                extra_context[f'{platform}_info'] = platform_admin.template_extra_info(request)
            except AttributeError:
                pass  # Skip if template_extra_info is not implemented

        return super(APIVariableAdmin, self).changelist_view(
            request, extra_context=extra_context
        )


@admin.register(ServerVariable)
class ServerVariableAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    list_editable = ('value',)

    search_fields = ('key', 'value')

    readonly_fields = ('tooltip',)


def template_extra_info(request):
    return None
