from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse
from patreon import OAuth, API

from config.models import APIVariable, get_api_vars
from game.models import GameCode, Backer
from patreon_auth.admin import get_patreon_redirect_uri, fetch_patreon_info


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

    client_id = APIVariable.objects.get(key='PATREON_CLIENT_ID').value

    try:
        campaign_title = APIVariable.objects.get(key='CAMPAIGN_TITLE').value
    except ObjectDoesNotExist:
        campaign_title = 'Unreal Engine Game'

    try:
        terms_conditions_url = APIVariable.objects.get(key='TERMS_CONDITIONS_URL').value
        privacy_policy_url = APIVariable.objects.get(key='PRIVACY_POLICY_URL').value
    except ObjectDoesNotExist:
        terms_conditions_url = ''
        privacy_policy_url = ''

    ctx = {
        'state': quote(request.GET['r']),
        'client_id': client_id,
        'redirect_uri': get_patreon_redirect_uri(),
        'project_title': campaign_title,
        'terms_conditions_url': terms_conditions_url,
        'privacy_policy_url': privacy_policy_url,
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

    # Request pledge and user info from Patreon
    client_id = api_vars.get('PATREON_CLIENT_ID', '')
    client_secret = api_vars.get('PATREON_CLIENT_SECRET', '')

    oauth_client = OAuth(client_id, client_secret)
    tokens = oauth_client.get_tokens(request.GET['code'], get_patreon_redirect_uri())

    if 'access_token' not in tokens:
        # Bad Patreon API token
        return HttpResponseServerError('Bad Patreon API token')

    access_token = tokens['access_token']
    api_client = API(access_token)

    user_response = api_client.fetch_user()
    try:
        user = user_response.data()
    except AttributeError:
        # Unable to access user information
        return HttpResponseBadRequest('Unable to access user information')

    if user.id() == api_vars.get('PATREON_CREATOR_ID', ''):
        # it's the creator so access_token is invalidated
        api_token, _ = APIVariable.objects.get_or_create(key='PATREON_ACCESS_TOKEN')
        api_token.value = access_token
        api_token.save()
        api_refresh_token, _ = APIVariable.objects.get_or_create(key='PATREON_REFRESH_TOKEN')
        api_refresh_token.value = tokens.get('refresh_token', '')
        api_refresh_token.save()

    pledges = user.relationship('pledges')
    pledge = pledges[0] if pledges and len(pledges) > 0 else None

    # Create/fetch backer
    try:
        backer = Backer.get_patreon(patreon_user=user, patreon_pledge=pledge)
    except ObjectDoesNotExist:
        backer = None

    if backer is None:
        # Could not create backer
        return HttpResponseBadRequest('Could not create backer')

    # If pledge is valid create the code for the backer
    request_body = request.GET['state']
    version_hash = request_body[-40:]
    decrypted_message = GameCode.decode_request(request_body=request_body.encode('utf-8'))

    if not decrypted_message:
        # Could not create the code
        return HttpResponseBadRequest('Could not create the code')

    try:
        GameCode.unregister(
            decrypted_message=decrypted_message,
            version_hash=version_hash,
        )
    except ObjectDoesNotExist:
        pass  # Silently ignore if wasn't able to unregister previous code
    except ValueError:
        pass  # Silently ignore if wasn't able to unregister previous code

    ctx = {
        'state': request_body,
        'project_title': api_vars.get('CAMPAIGN_TITLE', 'Unreal Engine Game'),
        'terms_conditions_url': api_vars.get('TERMS_CONDITIONS_URL', ''),
        'privacy_policy_url': api_vars.get('PRIVACY_POLICY_URL', ''),
        'creator_id': api_vars.get('PATREON_CREATOR_ID', ''),
    }
    ctx.update(decrypted_message)

    try:
        auth_code = GameCode(
            note=request_body,
            backer=backer
        )
        auth_code.clean()
        auth_code.save()
        # Code created, refresh the backer info
        return render(request=request, template_name='register_success.html', context=ctx)
    except ValidationError:
        # Could not create the code (%s) % e.message
        return render(request=request, template_name='become_patron.html', context=ctx)
