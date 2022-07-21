from urllib.parse import quote

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import GameCode


@csrf_exempt
def code(request):
    decrypted_message = GameCode.decode_request(request_body=request.body)

    if not decrypted_message or 'symmetric_key' not in decrypted_message:
        return HttpResponseBadRequest('Unable to decrypt the code.')

    version_hash = request.body[-40:].decode('utf-8')

    # Find the code if available
    try:
        auth_code = GameCode.objects.filter(
            instance_id=decrypted_message['instance_id'],
            version__version_hash=version_hash,
        ).latest('datetime')
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if not auth_code:
        return HttpResponseNotFound()

    # Unregister old code if appropriate
    if decrypted_message['old_signature'] and not\
        auth_code.auth_signature.startswith(
            decrypted_message['old_signature']):
        try:
            GameCode.unregister(
                decrypted_message=decrypted_message,
                version_hash=version_hash
            )
        except ObjectDoesNotExist:
            pass
        except ValueError:
            pass

    # Encrypt the code data and return to client
    try:
        return HttpResponse(auth_code.get_auth_code(
            symmetric_key=decrypted_message['symmetric_key']
        ))
    except (ValueError, TypeError):
        # If key in decrypted_message is incompatible
        return HttpResponseBadRequest('Bad Request')


def register(request):
    request_body = request.GET['r']
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
    redirect_uri = APIVariable.objects.get(key='PATREON_REDIRECT_URI').value

    try:
        campaign_title = APIVariable.objects.get(key='CAMPAIGN_TITLE').value
    except ObjectDoesNotExist:
        campaign_title = 'Unreal Engine Game'

    ctx = {
        'state': quote(request.GET['r']),
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'project_title': campaign_title,
    }
    ctx.update(decrypted_message)
    return render(
        request=request, template_name='patreon.html',
        context=ctx
    )


@csrf_exempt
def unregister(request):
    decrypted_message = GameCode.decode_request(request_body=request.body)

    if not decrypted_message:
        return HttpResponseBadRequest('Bad Request')

    try:
        GameCode.unregister(
            decrypted_message=decrypted_message,
            version_hash=request.body[-40:].decode('utf-8'),
        )
    except ObjectDoesNotExist:
        return HttpResponseNotFound('Not Found')
    except ValueError:
        return HttpResponseBadRequest('Unregister request failed')

    return HttpResponse('OK')

