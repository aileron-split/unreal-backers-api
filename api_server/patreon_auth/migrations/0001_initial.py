# Generated by Django 4.0.6 on 2022-07-23 17:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('config', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PatreonTier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reward_id', models.IntegerField(help_text='Patreon reward ID received with patron info', unique=True)),
                ('tier_status', models.CharField(choices=[('pu', 'Published'), ('ac', 'Active'), ('lg', 'Legacy')], default='ac', max_length=2)),
                ('tier_label', models.CharField(blank=True, help_text='Label for the Patreon tier/reward', max_length=256)),
                ('game_tier', models.ForeignKey(blank=True, help_text='Corresponding game benefit tier', null=True, on_delete=django.db.models.deletion.SET_NULL, to='config.gametier')),
            ],
        ),
    ]
