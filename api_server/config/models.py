import json
from hashlib import sha1
from os import makedirs

import patreon
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from patreon.jsonapi.parser import JSONAPIParser


class GameVersion(models.Model):
    version = models.CharField(max_length=256, blank=False, unique=True)

    authority_file: str = models.FileField(
        null=True, blank=True,
        upload_to=settings.AUTHORITY_ROOT,
        help_text='The authority .pem key file for the version'
    )

    version_hash: str = models.CharField(max_length=40, unique=True, db_index=True)

    note: str = models.TextField(default='', blank=True)

    datetime = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.version

    def make_hash(self):
        return sha1(str(self).encode('utf-8')).hexdigest()

    @property
    def public_key(self):
        with open(self.authority_file.path, 'rb') as key_file:
            private = serialization.load_pem_private_key(key_file.read(), password=None)
        public = private.public_key()
        pem_bytes = public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_bytes.decode('utf-8')

    def generate_authority_file(self):
        filename = f'{slugify(self.version)}.pem'
        path = settings.MEDIA_ROOT / settings.AUTHORITY_ROOT / filename

        makedirs(settings.MEDIA_ROOT / settings.AUTHORITY_ROOT, exist_ok=True)

        if not path.exists():
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(path, 'wb+') as key_file:
                key_file.write(pem)
        return str(settings.AUTHORITY_ROOT / filename)

    def clean(self):
        self.version_hash = self.make_hash()
        self.authority_file = self.generate_authority_file()


class GameTier(models.Model):
    tier_code = models.CharField(
        max_length=8, unique=True, blank=False,
        help_text='8-character long tier id sent to the game'
    )
    tier_label = models.CharField(
        max_length=256, blank=False,
        help_text='Label for the game tier'
    )

    def __str__(self):
        return f'{self.tier_label} [{self.tier_code}]'


class ServerVariable(models.Model):
    key = models.CharField(max_length=1024, primary_key=True)
    value = models.CharField(max_length=1024, blank=True)
    tooltip = models.CharField(max_length=1024, blank=True)

    class Meta:
        verbose_name_plural = 'Server config'

    def __str__(self):
        return self.key


# Server Configuration
class APIVariable(models.Model):
    key = models.CharField(max_length=1024, primary_key=True)
    value = models.CharField(max_length=1024, blank=True)
    tooltip = models.CharField(max_length=1024, blank=True)

    class Meta:
        verbose_name_plural = 'API config'

    def __str__(self):
        return self.key

    def clean(self):
        # Automagically set Campaign Title from Patreon if available
        if self.key == 'PATREON_ACCESS_TOKEN':
            api_client = patreon.API(access_token=self.value)
            if api_client:
                campaign_response = api_client.fetch_campaign(includes=('creator',))
                if type(campaign_response) is JSONAPIParser:
                    if not APIVariable.objects.filter(key='CAMPAIGN_TITLE').exists():
                        try:
                            campaign = campaign_response.data()[0]
                            title = APIVariable(
                                key='CAMPAIGN_TITLE',
                                value=campaign.attributes().get('creation_name', 'Creation Title')
                            )
                            title.save()
                        except AttributeError:
                            # Failed setting CAMPAIGN_TITLE
                            pass
                    creator_id, _ = APIVariable.objects.get_or_create(key='PATREON_CREATOR_ID')
                    creator_id.value = campaign_response.json_data['data'][0]['relationships']['creator']['data']['id']
                    creator_id.save()
        else:
            # Skip setting CAMPAIGN_TITLE
            pass


def add_default_api_vars(default_api_vars):
    for line in default_api_vars:
        obj, created = APIVariable.objects.get_or_create(key=line['key'])
        if created:
            obj.value = line['default']
            obj.tooltip = line['desc']
            obj.save()


def get_api_vars():
    return {v.key: v.value for v in APIVariable.objects.all()}


def get_server_vars():
    return {v.key: v.value for v in ServerVariable.objects.all()}
