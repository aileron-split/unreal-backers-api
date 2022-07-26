from textwrap import dedent

from django.test import TestCase

# Create your tests here.
from config.models import GameVersion, GameTier
from game.models import Backer, GameCode


class BackerCodeTestCase(TestCase):
    def setUp(self) -> None:
        version = GameVersion(version='v1.0 [test]', note='Backer Code unit test')
        version.clean()
        version.save()
        tier = GameTier.objects.create(tier_code='test', tier_label='Test Tier')
        backer = Backer.objects.create(
            display_name='UnitTest Account',
            url='https://aileron.hr',
            tier=tier,
            note='Backer Code unit test'
        )
        code = GameCode(
            instance_id='x' * 32,
            version=version,
            backer=backer,
            note='Backer Code unit test'
        )
        code.clean()
        code.save()

    def test_version_hash_created(self):
        version = GameVersion.objects.get(version='v1.0 [test]')
        self.assertEqual(len(version.version_hash), 40)
