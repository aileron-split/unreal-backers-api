import patreon
from django.db import models

import config.models
from config.models import GameTier, APIVariable, get_api_vars


def get_patreon_api():
    api_vars = get_api_vars()

    access_token = api_vars.get('PATREON_ACCESS_TOKEN', '')

    if not access_token:
        add_default_api_vars(DEFAULT_API_CONFIG_LINES)
        return

    patreon_api = patreon.API(access_token=access_token)

    if not patreon_api:
        # Try to refresh access token
        refresh_token = api_vars.get('PATREON_REFRESH_TOKEN', '')
        if not refresh_token:
            info['error'] = 'Patreon API fail'
            return info

        client_id = api_vars.get('PATREON_CLIENT_ID', '')
        client_secret = api_vars.get('PATREON_CLIENT_SECRET', '')

        oauth_client = OAuth(client_id, client_secret)
        tokens = oauth_client.refresh_token(refresh_token, get_patreon_redirect_uri())

        if 'access_token' in tokens:
            access_token = tokens['access_token']
            api_token, _ = APIVariable.objects.get_or_create(key='PATREON_ACCESS_TOKEN')
            api_token.value = access_token
            api_token.save()
            api_refresh_token, _ = APIVariable.objects.get_or_create(key='PATREON_REFRESH_TOKEN')
            api_refresh_token.value = tokens.get('refresh_token', '')
            api_refresh_token.save()

            patreon_api = patreon.API(access_token=access_token)
        else:
            info['error'] = 'Patreon API fail'
            return info

    return patreon_api


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
            patreon_api = get_patreon_api()
            if patreon_api:
                campaign_response = api_client.fetch_campaign(includes=('rewards',))
                try:
                    included = campaign_response.json_data['included']
                    reward_titles = {
                        int(i['id']): i['attributes']['title']
                        for i in included if i.get('type', '') == 'reward' and int(i['id']) > 0
                    }
                    self.tier_label = reward_titles.get(self.reward_id, '')
                except AttributeError:
                    # Failed setting Patreon tier label.
                    pass


DEFAULT_API_CONFIG_LINES = [
    {'key': 'PATREON_CLIENT_ID', 'default': '', 'desc': ''},
    {'key': 'PATREON_CLIENT_SECRET', 'default': '', 'desc': ''},
    {'key': 'PATREON_ACCESS_TOKEN', 'default': '', 'desc': ''},
    {'key': 'PATREON_REFRESH_TOKEN', 'default': '', 'desc': ''},
    {'key': 'PATREON_CREATOR_ID', 'default': '', 'desc': ''},
    {'key': 'TERMS_CONDITIONS_URL', 'default': '', 'desc': ''},
    {'key': 'PRIVACY_POLICY_URL', 'default': '', 'desc': ''},
]

