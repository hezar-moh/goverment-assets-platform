import requests
import logging

logger = logging.getLogger('authentication')


class KeycloakAdminService:

    def __init__(self):
        from django.conf import settings
        self.server_url = settings.KEYCLOAK_SERVER_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID
        self.client_secret = settings.KEYCLOAK_CLIENT_SECRET
        self.admin_username = getattr(settings, 'KEYCLOAK_ADMIN_USERNAME', 'admin')
        self.admin_password = getattr(settings, 'KEYCLOAK_ADMIN_PASSWORD', 'admin123')

    def _get_admin_token(self):
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
        token = self._get_admin_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
        }

    def create_user(self, username, email, first_name, last_name, password, role, ministry_schema):
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

        location = create_response.headers.get('Location', '')
        keycloak_id = location.split('/')[-1]

        if not keycloak_id:
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
            self.delete_user(keycloak_id)
            raise Exception(
                f"Failed to set password for '{username}' in Keycloak. "
                f"Status: {password_response.status_code}"
            )

        logger.info(
            f"Keycloak: Created user '{username}' with ID {keycloak_id}"
        )

        return keycloak_id

    def get_user_id(self, username):
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

    def get_user(self, keycloak_id):
        headers = self._get_headers()
        url = f"{self.server_url}/admin/realms/{self.realm}/users/{keycloak_id}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"Keycloak: Failed to fetch user {keycloak_id}. Status: {response.status_code}")
        return None

    def list_users_page(self, first=0, max=100):
        headers = self._get_headers()
        url = f"{self.server_url}/admin/realms/{self.realm}/users?first={first}&max={max}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"Keycloak: Failed to list users. Status: {response.status_code}")
        return []

    def get_all_users(self):
        all_users = []
        first = 0
        page_size = 100
        while True:
            batch = self.list_users_page(first=first, max=page_size)
            if not batch:
                break
            all_users.extend(batch)
            if len(batch) < page_size:
                break
            first += page_size
        return all_users

    def ensure_custom_attributes_defined(self):
        headers  = self._get_headers()
        url = f"{self.server_url}/admin/realms/{self.realm}/users/profile"

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("Could not fetch user profile (old Keycloak?).")
            return

        profile = resp.json()
        existing = {a['name'] for a in profile.get('attributes', [])}
        to_add = []

        if 'role' not in existing:
            to_add.append({
                'name': 'role',
                'displayName': 'Role',
                'permissions': {
                    'view': ['admin', 'user'],
                    'edit': ['admin', 'user'],
                },
                'multivalued': False,
            })
        if 'ministry_schema' not in existing:
            to_add.append({
                'name': 'ministry_schema',
                'displayName': 'Ministry Schema',
                'permissions': {
                    'view': ['admin', 'user'],
                    'edit': ['admin', 'user'],
                },
                'multivalued': False,
            })

        if not to_add:
            return

        profile['attributes'] = profile.get('attributes', []) + to_add
        put_resp = requests.put(url, json=profile, headers=headers, timeout=10)
        if put_resp.status_code not in (200, 204):
            logger.error(
                f"Failed to update user profile: {put_resp.status_code} "
                f"{put_resp.text}"
            )
        else:
            logger.info(
                f"Added custom attributes to realm profile: "
                f"{[a['name'] for a in to_add]}"
            )

    def reset_password(self, keycloak_id, new_password):
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
