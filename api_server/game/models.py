from base64 import b64encode, b64decode
from datetime import datetime
from hashlib import md5
from itertools import zip_longest
from subprocess import Popen, PIPE

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone

from config.models import GameTier, GameVersion


def new_aes_256_cbc():
    return os.urandom(32)


class Licensee(models.Model):
    url = models.URLField(
        blank=False, unique=True,
        help_text='URL of the person associated with this code (Patreon.com personal page)')
    email = models.EmailField(
        blank=True,
        help_text='Email of the person associated with this code')
    tier: GameTier = models.ForeignKey(
        GameTier, on_delete=models.RESTRICT, blank=True, null=True,
        help_text='Game benefits tier (derived from Patreon.com tiers)')
    display_name = models.CharField(
        max_length=100,
        help_text='Licensee name displayed in the simulator UI')
    note = models.TextField(default='', blank=True)

    datetime: datetime = models.DateTimeField(default=timezone.now, help_text='Created timestamp')

    def __str__(self):
        return '%s (%s)' % (self.display_name, self.url)

    @staticmethod
    def get_patreon(patreon_user, patreon_pledge):
        # Find the user if already registered or create a new one if not
        licensee, was_created = Licensee.objects.get_or_create(url=patreon_user.attribute('url'))

        # Update the licensee information
        licensee.display_name = patreon_user.attribute('vanity') or patreon_user.attribute('full_name')
        licensee.email = patreon_user.attribute('email')

        # Update the tier
        try:
            reward_id = patreon_pledge.json_data['relationships']['reward']['data']['id']
            licensee.tier = PatreonTier.objects.get(reward_id=reward_id).game_tier
        except AttributeError:
            licensee.tier = None

        # Save updated info
        licensee.save()

        return licensee


class ArchivedCode(models.Model):
    instance_id = models.CharField(
        max_length=32,
        help_text='LoginID provided by Unreal Engine')
    code_tier = models.ForeignKey(
        GameTier, on_delete=models.RESTRICT, blank=True, null=True,
        help_text='Game benefits tier stored on code creation')
    licensee = models.ForeignKey(Licensee, on_delete=models.RESTRICT)
    version = models.ForeignKey(GameVersion, on_delete=models.RESTRICT)
    note = models.TextField(default='', blank=True)
    auth_signature = models.TextField(
        blank=False,
        help_text='Signature for validating the code data')
    code_datetime: datetime = models.DateTimeField(
        help_text='Code creation timestamp')
    archived_datetime: datetime = models.DateTimeField(
        default=timezone.now,
        help_text='Archived timestamp')


class GameCode(models.Model):
    instance_id = models.CharField(
        max_length=32,
        help_text='Login ID provided by Unreal Engine')
    code_tier: GameTier = models.ForeignKey(
        GameTier, on_delete=models.RESTRICT, blank=True, null=True,
        help_text='Game benefits tier stored on code creation')
    licensee: Licensee = models.ForeignKey(Licensee, on_delete=models.CASCADE)
    version: GameVersion = models.ForeignKey(GameVersion, on_delete=models.CASCADE)
    note = models.TextField(
        default='', blank=True,
        help_text='NOTE: If Instance ID is blank, code request string can be pasted in here to \
         automatically fill in the data.'
    )
    auth_signature: str = models.TextField(
        blank=False,
        help_text='Signature for validating the code data')
    datetime: datetime = models.DateTimeField(
        default=timezone.now,
        help_text='Created timestamp')

    def clean(self):
        if not hasattr(self, 'instance_id') or len(self.instance_id) == 0:
            if not hasattr(self, 'note') or not self.note:
                raise ValidationError('Instance ID must be provided either directly or by pasting ' +
                                      'a code request string into the Note field')
            try:
                message = self.note
                decrypted_message = GameCode.decode_request(request_body=message.encode('utf-8'))
                self.instance_id = decrypted_message['instance_id']
                self.note = decrypted_message['note']

                version_hash = message[-40:]
                self.version = GameVersion.objects.get(version_hash=version_hash)
            except ObjectDoesNotExist:
                raise ValidationError('Invalid code request string')
        elif len(self.instance_id) != 32:
            raise ValidationError('Invalid Instance ID')

        if not hasattr(self, 'version') or not self.version:
            raise ValidationError('Version is required')

        if not hasattr(self, 'licensee') or not self.licensee:
            raise ValidationError('Licensee is required')

        if not hasattr(self, 'code_tier') or not self.code_tier:
            if self.licensee.tier is not None:
                self.code_tier = self.licensee.tier
            else:
                raise ValidationError('A valid Patreon subscription is required')

        self.sign_the_code()

    def __str__(self):
        return self.instance_id

    def get_auth_code(self, symmetric_key):
        # Append base64 encoded signature to the code_data and
        # encrypt with client's AES-256-ECB key.

        code_content = '|'.join((self.code_data(), self.auth_signature))

        key = b64decode(symmetric_key)

        # Encrypt with symmetric key
        padder = PKCS7(algorithms.AES(key).block_size).padder()
        padded_bytes = padder.update(code_content.encode('utf-8'))
        padded_bytes += padder.finalize()

        encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
        ct = encryptor.update(padded_bytes) + encryptor.finalize()

        return b64encode(ct).decode('utf-8')

    def code_data(self):
        return '|'.join((
            self.instance_id,
            self.code_tier.tier_code,
            self.licensee.display_name,
            self.version.version_hash,
            self.datetime.strftime("%Y-%m-%d"),
        ))

    def archive_code(self):
        ArchivedCode(
            instance_id=self.instance_id,
            code_tier=self.code_tier,
            licensee=self.licensee,
            version=self.version,
            note=self.note,
            auth_signature=self.auth_signature,
            code_datetime=self.datetime
        ).save()
        self.delete()

    @staticmethod
    def decode_request(request_body):
        # Extract version_hash and decrypt the request with the version's RSA key
        #
        # Note:
        # printf "Unnamed|0d9c7e62da275889c8b51a018b8dcdeb|<symmetric_key>|Y7mUiYkxyFw+5bIClfMy3mfkjPr..." |
        # openssl pkeyutl -inkey ~/.authority/Authority.pem -encrypt |
        # base64 -w0; echo
        #
        # printf "Y7mUiYkxyFw+5bIClfMy3mfkjPrfkqoVT70...Ec3yKP9zOivHsAoyWXhW5JA==" | base64 -d |
        # openssl pkeyutl -inkey ~/.authority/Authority.pem -decrypt; echo

        if len(request_body) < 384:
            return

        version_hash = request_body[-40:].decode('utf-8')
        message = request_body[:-40].decode('utf-8')

        # Get the version info
        try:
            version = GameVersion.objects.get(version_hash=version_hash)
        except ObjectDoesNotExist:
            return

        # Decrypt request data with private key
        with open(version.authority_file.path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
        data = private_key.decrypt(b64decode(message), PKCS1v15())

        return dict(zip_longest(
            ('note', 'instance_id', 'symmetric_key', 'old_signature'),
            # stdout.decode('utf-8').split('|'),
            data.decode('utf-8').split('|'),
            fillvalue=None  # Has to be None so that unregister fails without code
        ))

    def sign_the_code(self):
        # Sign [code_data] with RSA key, and store the base64 encoded signature.
        #
        # Note:
        # printf "0d9c7e62da275889c8b51a018b8dcdeb|pilot|Manfred|1935752234088401da4832311af118955a1ccd85|2020-11-15" |
        # openssl pkeyutl -inkey ~/.authority/Authority.pem -sign -pkeyopt digest:sha256 |
        # base64 -w0; echo

        data_bytes = self.code_data().encode('utf-8')
        digest = md5(data_bytes).hexdigest().encode('utf-8')

        # Sign with RSA and return the signature
        # data_bytes = '2f7446b7901e465bbc65402f435345fe'.encode('utf-8')
        # with open(self.version.authority_file.path, 'rb') as key_file:
        #     private_key = serialization.load_pem_private_key(
        #         key_file.read(), password=None
        #     )
        # signature = private_key.sign(data_bytes, padding.PKCS1v15(), hashes.SHA256())
        # self.auth_signature = b64encode(signature).decode('utf-8')

        stdout, stderr = Popen(
            ['openssl', 'pkeyutl', '-inkey', self.version.authority_file.path,
             '-sign', '-pkeyopt', 'digest:sha256'],
            stdin=PIPE, stdout=PIPE
        ).communicate(digest)  # self.code_content().encode('utf-8'))
        self.auth_signature = b64encode(stdout).decode('utf-8')

    @staticmethod
    def unregister(decrypted_message, version_hash):
        codes = GameCode.objects.filter(
            instance_id=decrypted_message['instance_id'],
            version__version_hash=version_hash,
            auth_signature__startswith=decrypted_message['old_signature'],
        )

        if not codes:
            raise ObjectDoesNotExist()

        for code in codes:
            code.archive_code()
