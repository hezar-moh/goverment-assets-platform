# Purpose: Talks to the Keycloak Admin REST API — create, update, delete users, reset passwords.

import requests
import logging

logger = logging.getLogger('authentication')


class KeycloakAdminService:
    """Manages users in Keycloak via the Admin API. Gets a fresh admin token for each operation."""

    def __init__(self):
        from django.conf import settings
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self.admin_username = getattr(settings, 'KEYCLOAK_ADMIN_USERNAME', 'admin')
        self.admin_password = getattr(settings, 'KEYCLOAK_ADMIN_PASSWORD', 'admin123')

    def _get_admin_token(self):
        """Get a short-lived admin token from the Keycloak master realm."""
        token_url = f"{self.server_url}/realms/master/protocol/openid-connect/token"

        response = requests.post(
            token_url,
            data={
                'grant_type': 'password',
                'client_id':  'admin-cli',
                'username':   self.admin_username,
                'password':   self.admin_password,
            },
            timeout=10
        )

        if response.status_code != 200:
            logger.error(
                f"Keycloak admin token failed: {response.status_code} "
                f"{response.text}"
            )
            raise Exception(
                f"Cannot connect to Keycloak admin. "
                f"Status: {response.status_code}"
            )

        return response.json()['access_token']

    def _get_headers(self):
        """Build headers with a fresh admin token."""
        token = self._get_admin_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        }

    def create_user(self, username, email, first_name, last_name, password, role, ministry_schema):
        """Create a user in Keycloak (creates user, then sets password in a separate call). Returns the keycloak_id UUID."""
        headers  = self._get_headers()
        base_url = f"{self.server_url}/admin/realms/{self.realm}"

        user_data = {
            'username':   username,
            'email':      email,
            'firstName':  first_name,
            'lastName':   last_name,
            'enabled':    True,
            'attributes': {
                'role':            [role],
                'ministry_schema': [ministry_schema or ''],
            }
        }

        create_response = requests.post(
            f"{base_url}/users",
            json=user_data,
            headers=headers,
            timeout=10
        )

        if create_response.status_code == 409:
            raise Exception(f"Username '{username}' already exists in Keycloak.")

        if create_response.status_code not in [201, 200]:
            raise Exception(
                f"Failed to create user in Keycloak. "
                f"Status: {create_response.status_code}. "
                f"Response: {create_response.text}"
            )

        # Keycloak returns the new user's UUID in the Location header
        location = create_response.headers.get('Location', '')
        keycloak_id = location.split('/')[-1]

        if not keycloak_id:
            # If Location header missing, search by username
            keycloak_id = self.get_user_id(username)

        if not keycloak_id:
            raise Exception(
                f"User created in Keycloak but could not retrieve UUID "
                f"for username '{username}'"
            )

        password_response = requests.put(
            f"{base_url}/users/{keycloak_id}/reset-password",
            json={
                'type':      'password',
                'value':     password,
                'temporary': False,
            },
            headers=headers,
            timeout=10
        )

        if password_response.status_code not in [204, 200]:
            self.delete_user(keycloak_id)  # rollback: don't leave a user without a password
            raise Exception(
                f"Failed to set password for '{username}' in Keycloak. "
                f"Status: {password_response.status_code}"
            )

        logger.info(
            f"Keycloak: Created user '{username}' with ID {keycloak_id}"
        )

        return keycloak_id

    def get_user_id(self, username):
        """Find a user in Keycloak by username and return their UUID."""
        headers = self._get_headers()
        base_url = f"{self.server_url}/admin/realms/{self.realm}"

        response = requests.get(
            f"{base_url}/users",
            params={'username': username, 'exact': 'true'},
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            users = response.json()
            if users:
                return users[0]['id']

        return None

    def delete_user(self, keycloak_id):
        """Delete a user from Keycloak by UUID. Used for rollback if Django user creation fails."""
        try:
            headers  = self._get_headers()
            base_url = f"{self.server_url}/admin/realms/{self.realm}"

            requests.delete(
                f"{base_url}/users/{keycloak_id}",
                headers=headers,
                timeout=10
            )
            logger.info(f"Keycloak: Deleted user {keycloak_id} (rollback)")
        except Exception as e:
            logger.error(f"Keycloak: Rollback delete failed: {e}")

    def update_user(self, keycloak_id, email=None, first_name=None, last_name=None,
                    role=None, ministry_schema=None, is_active=None):
        """Update a Keycloak user. Only changes fields that are provided (not None)."""
        headers = self._get_headers()
        base_url = f"{self.server_url}/admin/realms/{self.realm}"

        update_data = {}
        if email is not None: update_data['email'] = email
        if first_name is not None: update_data['firstName'] = first_name
        if last_name is not None: update_data['lastName'] = last_name
        if is_active is not None: update_data['enabled'] = is_active

        if role is not None or ministry_schema is not None:
            update_data['attributes'] = {}
            if role is not None: update_data['attributes']['role'] = [role]
            if ministry_schema is not None: update_data['attributes']['ministry_schema'] = [ministry_schema or '']

        if not update_data:
            return

        response = requests.put(f"{base_url}/users/{keycloak_id}", json=update_data, headers=headers, timeout=10)
        if response.status_code not in [204, 200]:
            raise Exception(f"Failed to update user in Keycloak. Status: {response.status_code}")
        logger.info(f"Keycloak: Updated user {keycloak_id}")

    def reset_password(self, keycloak_id, new_password):
        """Reset a user's password in Keycloak."""
        headers  = self._get_headers()
        base_url = f"{self.server_url}/admin/realms/{self.realm}"

        response = requests.put(
            f"{base_url}/users/{keycloak_id}/reset-password",
            json={
                'type':      'password',
                'value':     new_password,
                'temporary': False,
            },
            headers=headers,
            timeout=10
        )

        if response.status_code not in [204, 200]:
            raise Exception(
                f"Failed to reset password in Keycloak. "
                f"Status: {response.status_code}"
            )

        logger.info(f"Keycloak: Reset password for user {keycloak_id}")