from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import render

from config.models import GameTier


@permission_required(
    perm='config.view_gametier',
    login_url='/admin/login'
)
def tiers(request):
    tiers_list = ['---,"TierCode","TierLabel"'] +\
                 [f'"{tier.tier_code}","{tier.tier_code}","{tier.tier_label}"' for tier in GameTier.objects.all()]
    return HttpResponse(
        '\n'.join(tiers_list),
        content_type='text/csv; charset=utf-8',
        headers={
            'content-disposition': 'attachment;filename=GameTiersConfiguration.csv',
        }
    )
