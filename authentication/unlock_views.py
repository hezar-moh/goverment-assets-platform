"""Web view for self-service account unlock via email link."""
from django.shortcuts import render
import logging

logger = logging.getLogger('authentication')


def account_unlock_view(request, token):
    """GET /unlock-account/<uuid:token>/

    Validates the one-time unlock token, re-enables the account,
    clears login attempt records, and shows a result page.
    """
    from authentication.models import UnlockToken, LoginAttempt, CustomUser
    from django.utils import timezone

    try:
        token_obj = UnlockToken.objects.select_related('user').get(
            token=token
        )
    except UnlockToken.DoesNotExist:
        return render(request, 'authentication/unlock_result.html', {
            'success':    False,
            'page_title': 'Invalid Unlock Link',
            'message': (
                'This unlock link is invalid. It may have been '
                'used already or does not exist. '
                'Please contact your Ministry Administrator.'
            ),
        })

    if not token_obj.is_valid:
        return render(request, 'authentication/unlock_result.html', {
            'success':    False,
            'page_title': 'Unlock Link Expired',
            'message': (
                'This unlock link has expired or has already been '
                'used. Unlock links are valid for 1 hour. '
                'Please contact your Ministry Administrator to '
                'unlock your account manually.'
            ),
        })

    # Token is valid — unlock the account
    user = token_obj.user
    user.is_locked = False
    user.save(update_fields=['is_locked'])

    # Mark token as used
    token_obj.is_used = True
    token_obj.used_at = timezone.now()
    token_obj.save(update_fields=['is_used', 'used_at'])

    # Clear all LoginAttempt records for this user
    LoginAttempt.objects.filter(username=user.username).delete()

    # Write audit log
    if user.ministry_schema:
        try:
            from organizations.models import AuditLog
            from django_tenants.utils import schema_context
            with schema_context(user.ministry_schema):
                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=(
                        user.get_full_name() or user.username
                    ),
                    action='UPDATE',
                    model_name='CustomUser',
                    object_id=str(user.id),
                    object_repr=str(user),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        except Exception:
            pass

    logger.info(
        f"Account {user.username} unlocked via email token "
        f"from {request.META.get('REMOTE_ADDR')}"
    )

    return render(request, 'authentication/unlock_result.html', {
        'success':   True,
        'page_title': 'Account Unlocked',
        'username':  user.username,
        'message': (
            'Your account has been successfully unlocked. '
            'You can now log in. If you did not make these '
            'login attempts, please change your password '
            'immediately after logging in.'
        ),
    })
