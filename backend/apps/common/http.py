"""Request validation and transaction boundaries shared by business APIs."""
import json
from functools import wraps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.accounts.api import staff_api

class IntakeError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def endpoint(methods):
    def decorate(fn):
        @require_http_methods(methods)
        @staff_api
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            try:
                with transaction.atomic():
                    return fn(request, *args, **kwargs)
            except IntakeError as exc:
                return JsonResponse({'error': exc.message}, status=exc.status)
            except (ValidationError, ValueError, TypeError):
                return JsonResponse({'error': 'Invalid field value or record identifier'}, status=400)
            except (IntegrityError, OperationalError):
                return JsonResponse({'error': 'The record changed or the database is busy. Reload and retry.'}, status=409)
        return wrapped
    return decorate


def payload(request, allowed):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise IntakeError('Send a JSON object')
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise IntakeError('Unexpected fields in request')
    return data


def find(model, value):
    try:
        obj = model.objects.filter(pk=value).first()
    except (ValidationError, ValueError, TypeError):
        obj = None
    if obj is None:
        raise IntakeError(f'{model.__name__} not found', 404)
    return obj

