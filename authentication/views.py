# Purpose: Web views for login/logout and helper functions for brute force protection and pending access.

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from .decorators import login_required_custom
import logging

security_logger = logging.getLogger("authentication")


def login_view(request):
    """Show the login page. Clears stuck OIDC state and redirects to Keycloak SSO."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Read our pending-access flag BEFORE clearing oidc_ session keys.
    # pop() reads it once and removes it — a one-time notice.
    is_pending_block = request.session.pop('pending_access_notice', False)

    # Clear any stuck OIDC session state from a previous failed login
    # This prevents the "still thinking I am the wrong user" problem
    for key in list(request.session.keys()):
        if key.startswith('oidc_'):
            del request.session[key]

    error = request.GET.get('error', '')
    error_message = ''
    if error == 'auth_failed':
        if is_pending_block:
            error_message = (
                "Your account is not yet registered in our system. "
                "Your access request has been recorded and is now "
                "awaiting approval from your Ministry or System "
                "Administrator. Please try again once your account "
                "has been set up, or contact your administrator."
            )
        else:
            error_message = (
                "Previous login attempt failed. "
                "Please try signing in again."
            )

    return render(request, 'authentication/login.html', {
        'keycloak_login_url': '/oidc/authenticate/',
        'error_message': error_message,
    })


@login_required_custom
def logout_view(request):
    """Log out of Django and redirect to Keycloak to end the SSO session."""
    user = request.user

    # Write audit log before ending the session
    if user.ministry_schema:
        try:
            from organizations.models import AuditLog
            from django_tenants.utils import schema_context

            with schema_context(user.ministry_schema):
                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    action="LOGOUT",
                    model_name="CustomUser",
                    object_id=str(user.id),
                    object_repr=str(user),
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )
        except Exception:
            pass

    # Log the logout in security log
    security_logger.info(f"Logout: {user.username} from {get_client_ip(request)}")

    # Log out of Django session first
    logout(request)

    from django.conf import settings
    keycloak_logout_url = (
        f"{settings.OIDC_OP_LOGOUT_ENDPOINT}"
        f"?post_logout_redirect_uri=http://localhost:8000/login/"
        f"&client_id={settings.OIDC_RP_CLIENT_ID}"
    )
    return redirect(keycloak_logout_url)


def _get_login_attempt(username, ip_address):
    """Get or create a LoginAttempt record for this username + IP."""
    from authentication.models import LoginAttempt

    attempt, created = LoginAttempt.objects.get_or_create(
        username=username, ip_address=ip_address, defaults={"attempts": 0}
    )
    return attempt


def _record_failed_attempt(username, ip_address):
    """Increment the failed attempt counter. Lock the account if MAX_ATTEMPTS is reached."""
    from authentication.models import LoginAttempt
    from django.utils import timezone
    from datetime import timedelta

    attempt = _get_login_attempt(username, ip_address)

    if attempt.locked_until and timezone.now() >= attempt.locked_until:
        attempt.attempts = 0
        attempt.locked_until = None

    attempt.attempts += 1

    if attempt.attempts >= LoginAttempt.MAX_ATTEMPTS:
        attempt.locked_until = timezone.now() + timedelta(minutes=LoginAttempt.LOCKOUT_MINUTES)

    attempt.save()
    return attempt


def _clear_failed_attempts(username, ip_address):
    """Delete the LoginAttempt record after a successful login."""
    from authentication.models import LoginAttempt

    LoginAttempt.objects.filter(username=username, ip_address=ip_address).delete()


def _is_locked_out(username, ip_address):
    """Check if this username + IP is locked. Returns (is_locked, minutes_remaining)."""
    from authentication.models import LoginAttempt
    from django.utils import timezone

    try:
        attempt = LoginAttempt.objects.get(username=username, ip_address=ip_address)
        if attempt.locked_until and timezone.now() < attempt.locked_until:
            return True, attempt.minutes_remaining
        if attempt.locked_until and timezone.now() >= attempt.locked_until:
            attempt.attempts = 0
            attempt.locked_until = None
            attempt.save()
    except LoginAttempt.DoesNotExist:
        pass

    return False, 0


def get_client_ip(request):
    """Get the real client IP from X-Forwarded-For (proxies) or REMOTE_ADDR (direct)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _record_pending_access(username, email, full_name, reason, request):
    """
    Records a blocked login attempt in the PendingAccess table.
    Called when someone tries to login but is blocked for any reason.
    Never raises exceptions — logging must never block the main flow.
    """
    try:
        from authentication.models import PendingAccess

        PendingAccess.objects.create(
            username=username,
            email=email or "",
            full_name=full_name or "",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            status="PENDING",
        )
    except Exception:
        pass
