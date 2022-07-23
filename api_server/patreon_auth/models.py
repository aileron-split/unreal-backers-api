import patreon
from django.db import models

import config.models
from config.models import GameTier, APIVariable


class PatreonTier(models.Model):
    class PatreonTierStatus(models.TextChoices):
        PUBLISHED = ('pu', 'Published')
        ACTIVE = ('ac', 'Active')
        LEGACY = ('lg', 'Legacy')

    reward_id = models.IntegerField(
        unique=True, blank=False,
        help_text='Patreon reward ID received with patron info'
    )
    tier_status = models.CharField(
        max_length=2, blank=False, default=PatreonTierStatus.ACTIVE,
        choices=PatreonTierStatus.choices
    )
    tier_label = models.CharField(
        max_length=256, blank=True,
        help_text='Label for the Patreon tier/reward'
    )
    game_tier: GameTier = models.ForeignKey(
        GameTier, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Corresponding game benefit tier'
    )

    def __str__(self):
        return f'{self.tier_label} [{self.reward_id}]'

    def clean(self):
        if not self.tier_label:
            access_token = APIVariable.objects.get(key='PATREON_ACCESS_TOKEN').value
            api_client = patreon.API(access_token=access_token)
            if api_client:
                campaign_response = api_client.fetch_campaign(includes=('rewards',))
                try:
                    included = campaign_response.json_data['included']
                    reward_titles = {
                        int(i['id']): i['attributes']['title']
                        for i in included if i.get('type', '') == 'reward' and int(i['id']) > 0
                    }
                    self.tier_label = reward_titles.get(self.reward_id, '')
                except AttributeError:
                    print('Failed setting CAMPAIGN_TITLE')


DEFAULT_API_CONFIG_LINES = [
    {'key': 'PATREON_CLIENT_ID', 'default': '', 'desc': ''},
    {'key': 'PATREON_CLIENT_SECRET', 'default': '', 'desc': ''},
    {'key': 'PATREON_ACCESS_TOKEN', 'default': '', 'desc': ''},
    {'key': 'TERMS_CONDITIONS_URL', 'default': '', 'desc': ''},
    {'key': 'PRIVACY_POLICY_URL', 'default': '', 'desc': ''},
]

