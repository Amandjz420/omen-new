import json
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST


def onboarding_pending(user):
    """True while a provisioned account still holds its issued initial password.

    Compares the stored password hash rather than trusting the flag alone, so a
    password changed through the admin site or a shell also completes onboarding.
    """
    account = getattr(user, 'legacy_account', None)
    if account is None or not account.must_change_password:
        return False
    if account.issued_password_hash and user.password != account.issued_password_hash:
        account.must_change_password = False
        account.save(update_fields=['must_change_password'])
        return False
    return True


def staff_api(fn):
    @wraps(fn)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Sign in to continue'}, status=401)
        # Onboarding is enforced on the server. An account issued an initial
        # password reaches nothing but password setup and sign-out until it is
        # changed, and an existing session does not bypass this.
        if onboarding_pending(request.user):
            return JsonResponse({'error': 'Set a new password before continuing',
                                 'code': 'password_change_required'}, status=403)
        if not request.user.is_staff:
            return JsonResponse({'error': 'Staff access is required for this migration preview'}, status=403)
        return fn(request, *args, **kwargs)
    return wrapped


def body(request):
    try:
        value = json.loads(request.body)
        return value if isinstance(value, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


@require_GET
def session(request):
    return JsonResponse({'csrf': get_token(request), 'username': request.user.get_username() if request.user.is_authenticated else None,
                         'staff': request.user.is_authenticated and request.user.is_staff,
                         'password_change_required': request.user.is_authenticated and onboarding_pending(request.user)})


@require_POST
def sign_in(request):
    data = body(request)
    if not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
        return JsonResponse({'error': 'Enter your username and password'}, status=400)
    user = authenticate(request, username=data['username'], password=data['password'])
    # A provisioned account may sign in so it can complete onboarding, even
    # though it holds no business access yet.
    if user is None or not (user.is_staff or getattr(user, 'legacy_account', None) is not None):
        return JsonResponse({'error': 'Invalid staff credentials'}, status=401)
    login(request, user)
    return JsonResponse({'username': user.username, 'staff': user.is_staff, 'csrf': get_token(request),
                         'password_change_required': onboarding_pending(user)})


@require_POST
def change_password(request):
    """Complete onboarding. Available to any signed-in account; it is the only
    business-bearing action permitted while a password change is outstanding."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in to continue'}, status=401)
    data = body(request)
    current, new = data.get('current_password'), data.get('new_password')
    if not isinstance(current, str) or not isinstance(new, str):
        return JsonResponse({'error': 'Enter your current and new password'}, status=400)
    if not request.user.check_password(current):
        return JsonResponse({'error': 'Current password is incorrect'}, status=400)
    try:
        # Chosen passwords are validated in full, unlike the issued initial one.
        validate_password(new, user=request.user)
    except DjangoValidationError as exc:
        return JsonResponse({'error': 'Password rejected', 'problems': list(exc.messages)}, status=400)
    if new == current:
        return JsonResponse({'error': 'Choose a password you have not used here before'}, status=400)
    request.user.set_password(new)
    request.user.save(update_fields=['password'])
    account = getattr(request.user, 'legacy_account', None)
    if account is not None and account.must_change_password:
        account.must_change_password = False
        account.save(update_fields=['must_change_password'])
    update_session_auth_hash(request, request.user)
    return JsonResponse({'username': request.user.username, 'password_change_required': False})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})

