from django.contrib import admin

from .models import Backer, GameCode, ArchivedCode


@admin.register(Backer)
class BackerAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'url', 'email', 'tier', 'datetime', 'note')
    list_display_links = ('display_name',)

    list_filter = ('display_name', 'url', 'email', 'tier',)
    search_fields = ('display_name', 'url', 'email', 'note',)
    date_hierarchy = 'datetime'

    fields = ('display_name', 'url', 'email', 'tier', 'note', 'datetime',)


@admin.register(ArchivedCode)
class ArchivedCodeAdmin(admin.ModelAdmin):
    list_display = ('instance_id', 'code_tier', 'note', 'version', 'backer',
                    'code_datetime', 'archived_datetime', 'auth_signature')
    list_display_links = ('instance_id',)

    list_filter = ('version__version', 'code_tier', 'backer__tier')
    search_fields = ('backer__url', 'backer__email', 'backer__note', 'backer__display_name',
                     'backer__tier__tier_label', 'code_tier__tier_label',
                     'version__version_hash', 'instance_id', 'note',)
    date_hierarchy = 'archived_datetime'

    fields = ('instance_id', 'version', 'backer', 'note',
              'auth_signature', 'code_datetime', 'archived_datetime',)

    readonly_fields = ('instance_id', 'code_tier', 'version', 'backer', 'note',
                       'auth_signature', 'code_datetime', 'archived_datetime',)


@admin.register(GameCode)
class GameCodeAdmin(admin.ModelAdmin):
    list_display = ('instance_id', 'code_tier', 'note', 'version',
                    'backer', 'datetime', 'auth_signature')
    list_display_links = ('instance_id',)
    list_filter = ('version__version', 'code_tier', 'backer__tier')
    search_fields = ('backer__url', 'backer__email', 'backer__note', 'backer__display_name',
                     'backer__tier__tier_label', 'code_tier__tier_label',
                     'version__version_hash', 'instance_id', 'note',)

    date_hierarchy = 'datetime'

    fields = ('instance_id', 'code_tier', 'version', 'backer', 'note', 'auth_signature', 'datetime',)

    readonly_fields = ('datetime',)
    disabled_fields = ('auth_signature',)
    override_required_fields = ('backer', 'code_tier', 'version', 'instance_id', )

    actions = ['archive_selected_codes']

    @admin.action(
        description='Archive selected codes',
        permissions=['delete']
    )
    def archive_selected_codes(self, request, queryset):
        for code in queryset:
            code.archive_code()

    @staticmethod
    def tier(obj):
        return obj.backer.tier

    def get_form(self, *args, **kwargs):
        form = super(GameCodeAdmin, self).get_form(*args, **kwargs)
        for field_name in self.disabled_fields:
            form.base_fields[field_name].disabled = True
            form.base_fields[field_name].required = False

        for field_name in self.override_required_fields:
            form.base_fields[field_name].required = False

        return form
