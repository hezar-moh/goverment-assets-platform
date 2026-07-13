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

    # Read one-time session flags before clearing oidc_ keys
    is_pending_block     = request.session.pop('pending_access_notice', False)
    is_account_locked    = request.session.pop('account_locked_notice', False)
    is_account_deactived = request.session.pop('account_deactivated_notice', False)

    # Clear any stuck OIDC session state from a previous failed login
    for key in list(request.session.keys()):
        if key.startswith('oidc_'):
            del request.session[key]

    error = request.GET.get('error', '')
    error_message = ''

    if is_account_locked:
        error_message = (
            "Your account has been disabled due to multiple "
            "failed login attempts. An unlock link has been "
            "sent to your registered email address. If you "
            "did not receive it, contact your Ministry "
            "Administrator to restore access."
        )
    elif is_account_deactived:
        error_message = (
            "Your account has been deactivated by an administrator. "
            "Please contact your Ministry Administrator to "
            "restore access."
        )
    elif error == 'auth_failed':
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


def get_client_ip(request):
    """Get the real client IP from X-Forwarded-For (proxies) or REMOTE_ADDR (direct)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

