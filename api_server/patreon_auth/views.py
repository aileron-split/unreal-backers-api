from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.urls import reverse
from patreon import OAuth, API

from config.models import APIVariable


def authorize(request):
    if 'code' not in request.GET:
        # Bad Request Params
        return HttpResponseBadRequest('Bad request params')

    # Request pledge and user info from Patreon
    client_id = APIVariable.objects.get(key='PATREON_CLIENT_ID').value
    client_secret = APIVariable.objects.get(key='PATREON_CLIENT_SECRET').value
    redirect_uri = request.build_absolute_uri(reverse('patreon_authorize'))

    oauth_client = OAuth(client_id, client_secret)
    tokens = oauth_client.get_tokens(request.GET['code'], redirect_uri)

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

    pledges = user.relationship('pledges')
    pledge = pledges[0] if pledges and len(pledges) > 0 else None

    # Create/fetch licensee
    try:
        licensee = Licensee.get_patreon(patreon_user=user, patreon_pledge=pledge)
    except ObjectDoesNotExist:
        licensee = None

    if licensee is None:
        # Could not create licensee
        return HttpResponseBadRequest('Could not create licensee')

    # If pledge is valid create the code for the licensee
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

    try:
        campaign_title = APIVariable.objects.get(key='CAMPAIGN_TITLE').value
    except ObjectDoesNotExist:
        campaign_title = 'Unreal Engine Game'

    ctx = {
        'state': request_body,
        'project_title': campaign_title,
    }
    ctx.update(decrypted_message)

    try:
        auth_code = GameCode(
            note=request_body,
            licensee=licensee
        )
        auth_code.clean()
        auth_code.save()
        # Code created, refresh the license
        return render(request=request, template_name='register_success.html', context=ctx)
    except ValidationError as e:
        # Could not create the code (%s) % e.message
        return render(request=request, template_name='become_patron.html', context=ctx)
