import json
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse
from patreon import OAuth, API

from config.models import APIVariable, get_api_vars
from game.models import GameCode, Backer
from patreon_auth.admin import get_patreon_redirect_uri, fetch_patreon_info
from patreon_auth.models import refresh_access_token, PatreonTier


def register(request):
    request_body = request.GET.get('r', '')
    version_hash = request_body[-40:]
    decrypted_message = GameCode.decode_request(request_body=request_body.encode('utf-8'))

    if not decrypted_message:
        return HttpResponseBadRequest('Bad Request')

    try:
        GameCode.unregister(
            decrypted_message=decrypted_message,
            version_hash=version_hash,
        )
    except ObjectDoesNotExist:
        pass
    except ValueError:
        pass

    api_vars = get_api_vars()

    ctx = {
        'state': quote(request.GET['r']),
        'client_id': api_vars.get('PATREON_CLIENT_ID', ''),
        'redirect_uri': get_patreon_redirect_uri(),
        'project_title': api_vars.get('CAMPAIGN_TITLE', 'Unreal Engine Game'),
        'terms_conditions_url': api_vars.get('TERMS_CONDITIONS_URL', ''),
        'privacy_policy_url': api_vars.get('PRIVACY_POLICY_URL', ''),
    }
    ctx.update(decrypted_message)
    return render(
        request=request, template_name='patreon.html',
        context=ctx
    )


def authorize(request):
    if 'code' not in request.GET:
        # Bad Request Params
        return HttpResponseBadRequest('Bad request params')

    api_vars = get_api_vars()

    # Decrypt the state and create html template render context
    request_body = request.GET['state']
    version_hash = request_body[-40:]
    decrypted_message = GameCode.decode_request(request_body=request_body.encode('utf-8'))

    if not decrypted_message:
        # Could not create the code
        return HttpResponseBadRequest('Could not create the code')

    ctx = {
        'state': request_body,
        'project_title': api_vars.get('CAMPAIGN_TITLE', 'Unreal Engine Game'),
        'terms_conditions_url': api_vars.get('TERMS_CONDITIONS_URL', ''),
        'privacy_policy_url': api_vars.get('PRIVACY_POLICY_URL', ''),
        'creator_id': api_vars.get('PATREON_CREATOR_ID', ''),
    }
    ctx.update(decrypted_message)

    # Request pledge and user info from Patreon
    client_id = api_vars.get('PATREON_CLIENT_ID', '')
    client_secret = api_vars.get('PATREON_CLIENT_SECRET', '')
    creator_token = api_vars.get('PATREON_ACCESS_TOKEN', '')

    oauth_client = OAuth(client_id, client_secret)
    tokens = oauth_client.get_tokens(request.GET['code'], get_patreon_redirect_uri())

    if 'access_token' not in tokens:
        # Bad Patreon API token
        return HttpResponseServerError('Bad Patreon API token')

    access_token = tokens['access_token']

    response = requests.get(
        f'https://www.patreon.com/api/oauth2/v2/identity?include=memberships&fields[user]=full_name,url,email',
        headers={
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'Backers API',
        }
    )
    identity = json.loads(response.content)
    if 'errors' in identity:
        return HttpResponseServerError(f'Bad Patreon API request {identity["errors"]}')

    if identity['data']['id'] == api_vars.get('PATREON_CREATOR_ID', ''):
        # It's the creator so access_token is invalidated and should be refreshed.
        api_token, _ = APIVariable.objects.get_or_create(key='PATREON_ACCESS_TOKEN')
        api_token.value = access_token
        api_token.save()
        api_refresh_token, _ = APIVariable.objects.get_or_create(key='PATREON_REFRESH_TOKEN')
        api_refresh_token.value = tokens.get('refresh_token', '')
        api_refresh_token.save()

        # Update/create creator backer info
        user = identity['data']['attributes']
        backer, _ = Backer.objects.get_or_create(url=user['url'])
        backer.display_name = user['full_name']
        backer.email = user['email']
        backer.save()
    else:
        if 'included' in identity and identity['included']:
            member_id = identity['included'][0]['id']
        else:
            # Not a backer
            return render(request=request, template_name='become_patron.html', context=ctx)

        member_response = requests.get(
            f'https://www.patreon.com/api/oauth2/v2/members/{member_id}?include=user,currently_entitled_tiers&\
fields[user]=url&fields[member]=email,full_name,is_follower,lifetime_support_cents,patron_status',
            headers={
                'Authorization': f'Bearer {creator_token}',
                'User-Agent': 'Backers API',
            }
        )
        member_info = json.loads(member_response.content)
        if 'errors' in member_info:
            return HttpResponseServerError(f'Bad Patreon API request {member_info["errors"]}')

        member = member_info['data']['attributes']
        patreon_tier_id = member_info['data']['relationships']['currently_entitled_tiers']['data'][0]['id']
        user_url = None
        for i in member_info['included']:
            if i['type'] == 'user':
                user_url = i['attributes']['url']

        if not user_url:
            return HttpResponseServerError(f'Bad patron URL')

        try:
            game_tier = PatreonTier.objects.get(reward_id=patreon_tier_id).game_tier
        except ObjectDoesNotExist:
            return HttpResponseServerError(
                f'Bad server configuration ({patreon_tier_id}), please get in touch so we can fix it.'
            )

        # Create/fetch backer
        backer, _ = Backer.objects.get_or_create(url=user_url)
        backer.display_name = member['full_name']
        backer.email = member['email']
        backer.tier = game_tier
        backer.save()

    if backer is None:
        # Could not create backer
        return HttpResponseBadRequest('Could not create backer')

    # If pledge is valid create the code for the backer
    try:
        GameCode.unregister(
            decrypted_message=decrypted_message,
            version_hash=version_hash,
        )
    except ObjectDoesNotExist:
        pass  # Silently ignore if wasn't able to unregister previous code
    except ValueError:
        pass  # Silently ignore if wasn't able to unregister previous code

    try:
        auth_code = GameCode(note=request_body, backer=backer)
        auth_code.clean()
        auth_code.save()
        # Code created, refresh the backer info
        return render(request=request, template_name='register_success.html', context=ctx)
    except ValidationError:
        # Could not create the code (%s) % e.message
        return HttpResponseBadRequest('Could not create backer code')
