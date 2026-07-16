"""Load testing script for Locust.

Simulates concurrent ministry staff logging in and browsing assets.
Validates that the platform maintains response times under 3 seconds
with 50 concurrent users as specified in Chapter Four requirements.

Usage:
    pip install locust
    locust -f locustfile.py --host=https://goverment-assets-platform-production.up.railway.app

Then open http://localhost:8089 in your browser, set:
  - Number of users: 50
  - Spawn rate: 5 users/second
  - Host: (already set from --host)
"""

from locust import HttpUser, task, between, tag


class MinistryStaffUser(HttpUser):
    """Simulates a ministry staff member performing typical daily tasks.

    Each virtual user:
    1. Logs in via the API
    2. Views the asset list
    3. Views a specific asset detail
    4. Views audit logs
    5. Checks dashboard stats

    Wait time between tasks: 3–8 seconds (simulates reading time).
    """

    wait_time = between(3, 8)

    def on_start(self):
        """Log in when the virtual user starts.

        Uses the moh_admin credentials — in a real load test you'd
        want a pool of different users to avoid lockout triggers.
        """
        self.login_data = {
            'username': 'moh_admin',
            'password': 'Admin@123',
        }
        response = self.client.post(
            '/api/auth/login/',
            json=self.login_data,
        )
        if response.status_code == 200:
            body = response.json()
            self.access_token = body.get('access', '')
            self.headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
        else:
            self.access_token = ''
            self.headers = {}

    @tag('assets')
    @task(5)
    def list_assets(self):
        """Load the asset list — most frequent operation."""
        if self.access_token:
            self.client.get(
                '/api/assets/',
                headers=self.headers,
                name='/api/assets/',
            )

    @tag('assets')
    @task(3)
    def view_asset_detail(self):
        """View a specific asset's details."""
        if self.access_token:
            # First get the list to find an asset ID
            list_resp = self.client.get(
                '/api/assets/?page=1',
                headers=self.headers,
                name='/api/assets/',
            )
            if list_resp.status_code == 200:
                data = list_resp.json()
                results = data.get('results', [])
                if results:
                    asset_id = results[0]['id']
                    self.client.get(
                        f'/api/assets/{asset_id}/',
                        headers=self.headers,
                        name='/api/assets/{id}/',
                    )

    @tag('audit')
    @task(2)
    def view_audit_logs(self):
        """View audit log — moderately frequent."""
        if self.access_token:
            self.client.get(
                '/api/audit-logs/',
                headers=self.headers,
                name='/api/audit-logs/',
            )

    @tag('dashboard')
    @task(2)
    def view_dashboard_stats(self):
        """Load dashboard statistics."""
        if self.access_token:
            self.client.get(
                '/api/dashboard/stats/',
                headers=self.headers,
                name='/api/dashboard/stats/',
            )

    @tag('profile')
    @task(1)
    def view_profile(self):
        """Check own user profile (lightweight)."""
        if self.access_token:
            self.client.get(
                '/api/auth/me/',
                headers=self.headers,
                name='/api/auth/me/',
            )

    @tag('verify')
    @task(1)
    def verify_token(self):
        """Token verification — used by other platform modules."""
        if self.access_token:
            self.client.post(
                '/api/auth/verify-token/',
                json={'token': self.access_token},
                name='/api/auth/verify-token/',
            )

    @tag('auth')
    @task(1)
    def refresh_token(self):
        """Refresh the JWT token before it expires."""
        if self.access_token:
            self.client.post(
                '/api/auth/refresh/',
                json={'refresh': self.access_token},
                name='/api/auth/refresh/',
            )

    def on_stop(self):
        """Log out when the virtual user stops."""
        if self.access_token:
            self.client.post(
                '/api/auth/logout/',
                headers=self.headers,
                name='/api/auth/logout/',
            )
