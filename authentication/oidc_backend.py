# Purpose: Connects Keycloak SSO login to Django user accounts. Called by mozilla-django-oidc on every SSO login attempt.

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
import logging

logger = logging.getLogger('authentication')


class GovAssetOIDCBackend(OIDCAuthenticationBackend):
    """Bridge between Keycloak authentication and Django user accounts."""

    def filter_users_by_claims(self, claims):
        """Find a Django user matching the Keycloak token.

        Returns the user queryset so mozilla_django_oidc can call update_user().
        Actual blocking is done in get_user() which also checks is_locked.
        Session flags are set here so login_view() can show the right message.
        """
        from authentication.models import CustomUser

        logger.info(f"OIDC claims received: {claims}")

        keycloak_id = claims.get('sub', '')
        username = claims.get('preferred_username', '')

        user = None
        if keycloak_id:
            users = CustomUser.objects.filter(keycloak_id=keycloak_id)
            if users.exists():
                user = users.first()

        if not user and username:
            users = CustomUser.objects.filter(username=username)
            if users.exists():
                user = users.first()
                if not user.keycloak_id and keycloak_id:
                    user.keycloak_id = keycloak_id
                    user.save(update_fields=['keycloak_id'])
                    logger.info(f"OIDC: Linked {username} to {keycloak_id}")

        if user:
            # Sync is_active status FROM Keycloak (in case admin disabled user in Keycloak)
            if user.keycloak_id:
                try:
                    from authentication.keycloak_admin import KeycloakAdminService
                    kc = KeycloakAdminService()
                    kc_user = kc.get_user(user.keycloak_id)
                    if kc_user is not None:
                        kc_enabled = kc_user.get('enabled', True)
                        if kc_enabled != user.is_active:
                            user.is_active = kc_enabled
                            user.save(update_fields=['is_active'])
                            logger.info(
                                f"OIDC: Synced is_active={kc_enabled} for "
                                f"{username} from Keycloak"
                            )
                except Exception as e:
                    logger.warning(f"OIDC: Failed to sync status from Keycloak: {e}")

            # Set session flags so login_view can show the right message.
            # Actual blocking happens in get_user() below — we still return
            # the user queryset so update_user() runs, keeping data in sync.
            if user.is_locked:
                if self.request is not None:
                    self.request.session['account_locked_notice'] = True
            elif not user.is_active:
                if self.request is not None:
                    self.request.session['account_deactivated_notice'] = True

            logger.info(f"OIDC: Found user: {user.username}")
            return CustomUser.objects.filter(pk=user.pk)

        logger.warning(
            f"OIDC: No user found for username={username} keycloak_id={keycloak_id}"
        )
        return CustomUser.objects.none()

    def get_user(self, user_id):
        """Override to also block locked accounts (is_locked=True).

        The parent get_user() only checks is_active=True.
        We add the is_locked=False check so brute-force-locked users
        are blocked at the OIDC level too.
        """
        from authentication.models import CustomUser
        try:
            return CustomUser.objects.get(
                pk=user_id, is_active=True, is_locked=False
            )
        except CustomUser.DoesNotExist:
            return None

    def create_user(self, claims):
        """Block auto-creation and record in PendingAccess instead. Returns None to deny login."""
        username = claims.get('preferred_username', '')
        email = claims.get('email', '')
        full_name = claims.get('name', '')
        keycloak_id = claims.get('sub', '')
        ministry_schema = claims.get('ministry_schema', '')

        logger.warning(f"OIDC: No Django user found for Keycloak user: {username}. Access blocked.")

        try:
            from authentication.models import PendingAccess
            ip_address = ''
            user_agent = ''
            if self.request is not None:
                x_forwarded = self.request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded:
                    ip_address = x_forwarded.split(',')[0].strip()
                else:
                    ip_address = self.request.META.get('REMOTE_ADDR', '')
                user_agent = self.request.META.get('HTTP_USER_AGENT', '')[:500]

            PendingAccess.objects.create(
                username=username, email=email or '',
                full_name=full_name or '', keycloak_id=keycloak_id,
                ministry_schema=ministry_schema, status='PENDING',
                ip_address=ip_address or None,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"OIDC: Failed to create PendingAccess: {e}")

        if self.request is not None:
            self.request.session['pending_access_notice'] = True

        return None

    def update_user(self, user, claims):
        """Update the user's role and ministry_schema from Keycloak attributes on each login."""
        keycloak_id = claims.get('sub', '')
        ministry_schema = claims.get('ministry_schema', '')
        role = claims.get('role', '')
        update_fields = []

        if keycloak_id and not user.keycloak_id:
            user.keycloak_id = keycloak_id
            update_fields.append('keycloak_id')

        valid_roles = ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK', 'AUDITOR']
        if role and role in valid_roles and user.role != role:
            user.role = role
            update_fields.append('role')

        if ministry_schema and user.ministry_schema != ministry_schema:
            user.ministry_schema = ministry_schema
            update_fields.append('ministry_schema')

        if update_fields:
            user.save(update_fields=update_fields)
            logger.info(f"OIDC: Updated user {user.username} fields: {update_fields}")

        return user

    def get_userinfo(self, access_token, id_token, payload):
        """Get user info from the token payload."""
        return super().get_userinfo(access_token, id_token, payload)