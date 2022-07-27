from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
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

