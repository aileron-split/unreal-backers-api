import patreon
from django.contrib import admin, messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.text import slugify

from config.models import APIVariable, GameTier, add_default_api_vars
from .models import PatreonTier, DEFAULT_API_CONFIG_LINES


def fetch_patreon_info(request, auto_magic=False):
    info = {}
    try:
        access_token = APIVariable.objects.get(key='PATREON_ACCESS_TOKEN').value
    except ObjectDoesNotExist:
        access_token = ''
        add_default_api_vars(DEFAULT_API_CONFIG_LINES)
    api_client = patreon.API(access_token=access_token)

    if not api_client:
        info['error'] = 'Patreon API fail'
    else:
        campaign_response = api_client.fetch_campaign(includes=('rewards', 'creator'))
        try:
            campaign = campaign_response.data()[0]
            included = campaign_response.json_data['included']
            rewards = [
                {
                    'id': i['id'],
                    'title': i['attributes']['title'],
                    'url': i['attributes']['url'],
                    'published': i['attributes']['published']
                }
                for i in included if i.get('type', '') == 'reward' and int(i['id']) > 0
            ]

            if auto_magic:
                # Automagically update missing tiers in the database
                for reward in rewards:
                    tier, created = PatreonTier.objects.get_or_create(
                        reward_id=int(reward['id']),
                        tier_label=reward['title']
                    )
                    if created:
                        messages.info(request, f'Imported Patreon tier: {tier.tier_label} ({tier.reward_id})')

                # Update tier status
                active_tiers = [int(reward['id']) for reward in rewards]
                published_tiers = [int(reward['id']) for reward in rewards if reward['published']]
                for o in PatreonTier.objects.all():
                    current_status = PatreonTier.PatreonTierStatus.LEGACY
                    if o.reward_id in active_tiers:
                        if o.reward_id in published_tiers:
                            current_status = PatreonTier.PatreonTierStatus.PUBLISHED
                        else:
                            current_status = PatreonTier.PatreonTierStatus.ACTIVE
                    if current_status != o.tier_status:
                        o.tier_status = current_status
                        o.save()

            creator = [i for i in included if i.get('type', '') == 'user' and int(i['id']) > 0][0]

            info['rewards'] = rewards
            info['creator'] = creator
            info['campaign'] = campaign
        except AttributeError:
            # Unable to access user information
            info['error'] = 'Unable to access user information (possibly bad access token)'

    return info


@admin.register(PatreonTier)
class PatreonTierAdmin(admin.ModelAdmin):
    list_display = ('tier_label', 'reward_id', 'tier_status', 'game_tier')
    list_display_links = ('tier_label',)
    list_editable = ('game_tier',)

    list_filter = ('tier_status', 'game_tier')

    fields = ('reward_id', 'tier_label', 'game_tier')

    actions = ['mirror_tiers_to_game']

    @admin.action(
        description='Mirror selected to Game Tiers',
        permissions=['mirror']
    )
    def mirror_tiers_to_game(self, request, queryset):
        for tier in queryset:
            game_tier, created = GameTier.objects.get_or_create(
                tier_code=slugify(tier.tier_label)[:8],
                tier_label=tier.tier_label
            )
            game_tier.save()
            tier.game_tier = game_tier
            tier.save()

    @staticmethod
    def has_mirror_permission(request):
        return request.user.has_perm('config.add_gametier')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        info = fetch_patreon_info(request, auto_magic=True)
        extra_context['patreon_info'] = info

        return super(PatreonTierAdmin, self).changelist_view(
            request, extra_context=extra_context
        )
