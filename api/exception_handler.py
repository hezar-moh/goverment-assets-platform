from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data

        if isinstance(error_detail, dict):
            message = error_detail.get('detail', str(error_detail))
        elif isinstance(error_detail, list):
            message = ' '.join(str(e) for e in error_detail)
        else:
            message = str(error_detail)

        code_map = {
            400: 'bad_request',
            401: 'authentication_required',
            403: 'permission_denied',
            404: 'not_found',
            405: 'method_not_allowed',
            429: 'too_many_requests',
            500: 'server_error',
        }

        response.data = {
            'error':   True,
            'message': str(message),
            'code':    code_map.get(response.status_code, 'error'),
            'status':  response.status_code,
        }

    return response
