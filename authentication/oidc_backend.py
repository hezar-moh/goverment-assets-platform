# Purpose: Connects Keycloak SSO login to Django user accounts. Called by mozilla-django-oidc on every SSO login attempt.

from mozilla_django_oidc.auth import OIDCAuthenticationBackend
import logging

logger = logging.getLogger('authentication')


class GovAssetOIDCBackend(OIDCAuthenticationBackend):
    """Bridge between Keycloak authentication and Django user accounts."""

    def filter_users_by_claims(self, claims):
        """Find a Django user matching the Keycloak token. Tries keycloak_id first, then username."""
        from authentication.models import CustomUser

        logger.info(f"OIDC claims received: {claims}")

        keycloak_id = claims.get('sub', '')
        username = claims.get('preferred_username', '')

        if keycloak_id:
            users = CustomUser.objects.filter(keycloak_id=keycloak_id)
            if users.exists():
                logger.info(f"OIDC: Found by keycloak_id: {username}")
                return users

        if username:
            users = CustomUser.objects.filter(username=username)
            if users.exists():
                user = users.first()
                logger.info(f"OIDC: Found by username: {username}")
                if not user.keycloak_id and keycloak_id:
                    user.keycloak_id = keycloak_id
                    user.save(update_fields=['keycloak_id'])
                    logger.info(f"OIDC: Linked {username} to {keycloak_id}")
                return users

        logger.warning(f"OIDC: No user found for username={username} keycloak_id={keycloak_id}")
        return CustomUser.objects.none()

    def create_user(self, claims):
        """Block auto-creation and record in PendingAccess instead. Returns None to deny login."""
        username = claims.get('preferred_username', '')
        email = claims.get('email', '')
        full_name = claims.get('name', '')
        keycloak_id = claims.get('sub', '')

        logger.warning(f"OIDC: No Django user found for Keycloak user: {username}. Access blocked.")

        try:
            from authentication.models import PendingAccess
            PendingAccess.objects.create(
                username=username, email=email or '',
                full_name=full_name or '', keycloak_id=keycloak_id, status='PENDING',
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