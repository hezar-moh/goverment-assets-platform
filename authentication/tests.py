"""Unit tests for the authentication app.

Tests the CustomUser model, role properties, lockout mechanism,
PendingAccess workflow, and API permission classes.
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock

from authentication.models import (
    CustomUser, PendingAccess, LoginAttempt, UnlockToken, SuperAdminAuditLog,
)

UserModel = get_user_model()


# =============================================================================
# CustomUser Model Tests
# =============================================================================

class CustomUserModelTest(TestCase):
    """Verify the CustomUser model: roles, properties, and string representation."""

    def setUp(self):
        self.super_admin = UserModel.objects.create_user(
            username='superadmin', password='Admin@123',
            role='SUPER_ADMIN', ministry_schema=None,
        )
        self.ministry_admin = UserModel.objects.create_user(
            username='moh_admin', password='Admin@123',
            role='MINISTRY_ADMIN', ministry_schema='moh_schema',
        )
        self.facility_clerk = UserModel.objects.create_user(
            username='rad_clerk', password='Admin@123',
            role='FACILITY_CLERK', ministry_schema='moh_schema',
        )

    def test_super_admin_role_property(self):
        """is_super_admin should be True only for SUPER_ADMIN users."""
        self.assertTrue(self.super_admin.is_super_admin)
        self.assertFalse(self.ministry_admin.is_super_admin)

    def test_ministry_admin_property(self):
        """is_ministry_admin should be True only for MINISTRY_ADMIN users."""
        self.assertTrue(self.ministry_admin.is_ministry_admin)
        self.assertFalse(self.facility_clerk.is_ministry_admin)

    def test_default_role_is_facility_clerk(self):
        """A user created without specifying a role should default to FACILITY_CLERK."""
        user = UserModel.objects.create_user(
            username='default_user', password='Test@123',
        )
        self.assertEqual(user.role, 'FACILITY_CLERK')

    def test_string_representation(self):
        """__str__ should show full name and role."""
        self.super_admin.first_name = 'System'
        self.super_admin.last_name = 'Admin'
        expected = 'System Admin — SUPER_ADMIN'
        self.assertEqual(str(self.super_admin), expected)

    def test_super_admin_has_no_ministry_schema(self):
        """SUPER_ADMIN should have ministry_schema = None."""
        self.assertIsNone(self.super_admin.ministry_schema)

    def test_ministry_user_has_schema(self):
        """Ministry users should have the correct ministry_schema."""
        self.assertEqual(self.ministry_admin.ministry_schema, 'moh_schema')


# =============================================================================
# PendingAccess Model Tests
# =============================================================================

class PendingAccessModelTest(TestCase):
    """Verify that unauthenticated users are logged for admin review."""

    def setUp(self):
        self.pending = PendingAccess.objects.create(
            username='new_officer',
            email='officer@moh.go.tz',
            full_name='New Officer',
            keycloak_id='kc-uuid-123',
            ministry_schema='moh_schema',
            ip_address='192.168.1.100',
            user_agent='TestBrowser/1.0',
        )

    def test_pending_access_default_status(self):
        """New PendingAccess records should default to PENDING."""
        self.assertEqual(self.pending.status, 'PENDING')

    def test_pending_access_auto_timestamp(self):
        """attempted_at should be set automatically on creation."""
        self.assertIsNotNone(self.pending.attempted_at)

    def test_pending_access_string(self):
        """String representation should include username, status, and timestamp."""
        result = str(self.pending)
        self.assertIn('new_officer', result)
        self.assertIn('PENDING', result)


# =============================================================================
# LoginAttempt / Brute Force Protection Tests
# =============================================================================

class LoginAttemptModelTest(TestCase):
    """Verify progressive lockout: WARNING → COOLDOWN → DISABLED."""

    def setUp(self):
        self.attempt = LoginAttempt.objects.create(
            username='target_user',
            ip_address='10.0.0.1',
            attempts=0,
            stage='WARNING',
        )

    def test_initial_stage_is_warning(self):
        """New attempt records should start at WARNING stage."""
        self.assertEqual(self.attempt.stage, 'WARNING')

    def test_not_locked_when_no_cooldown(self):
        """is_locked should be False when locked_until is None."""
        self.attempt.locked_until = None
        self.assertFalse(self.attempt.is_locked)

    def test_locked_during_cooldown(self):
        """is_locked should be True when locked_until is in the future."""
        self.attempt.locked_until = timezone.now() + timedelta(minutes=5)
        self.assertTrue(self.attempt.is_locked)

    def test_unlocked_after_cooldown_expires(self):
        """is_locked should be False when locked_until is in the past."""
        self.attempt.locked_until = timezone.now() - timedelta(minutes=1)
        self.assertFalse(self.attempt.is_locked)

    def test_minutes_remaining_during_cooldown(self):
        """minutes_remaining should return positive int during cooldown."""
        self.attempt.locked_until = timezone.now() + timedelta(minutes=5)
        self.assertGreaterEqual(self.attempt.minutes_remaining, 1)

    def test_minutes_remaining_zero_when_not_locked(self):
        """minutes_remaining should be 0 when not in cooldown."""
        self.attempt.locked_until = None
        self.assertEqual(self.attempt.minutes_remaining, 0)


# =============================================================================
# UnlockToken Tests
# =============================================================================

class UnlockTokenModelTest(TestCase):
    """Verify one-time unlock tokens expire and invalidate correctly."""

    def setUp(self):
        self.user = UserModel.objects.create_user(
            username='locked_user', password='Test@123',
        )

    def test_token_valid_when_fresh(self):
        """A newly created token should be valid."""
        token = UnlockToken.create_for_user(self.user, validity_hours=1)
        self.assertTrue(token.is_valid)

    def test_token_invalid_after_use(self):
        """A used token should be invalid."""
        token = UnlockToken.create_for_user(self.user, validity_hours=1)
        token.is_used = True
        token.used_at = timezone.now()
        token.save()
        self.assertFalse(token.is_valid)

    def test_token_invalid_after_expiry(self):
        """An expired token should be invalid."""
        token = UnlockToken.create_for_user(self.user, validity_hours=0)
        self.assertFalse(token.is_valid)

    def test_create_for_user_invalidates_old_tokens(self):
        """Creating a new token should invalidate any existing unused tokens."""
        old_token = UnlockToken.create_for_user(self.user, validity_hours=1)
        new_token = UnlockToken.create_for_user(self.user, validity_hours=1)
        old_token.refresh_from_db()
        self.assertTrue(old_token.is_used)
        self.assertTrue(new_token.is_valid)


# =============================================================================
# API Permission Classes Tests
# =============================================================================

class PermissionClassesTest(TestCase):
    """Verify that DRF permission classes correctly block or allow access."""

    def setUp(self):
        from api.permissions import (
            IsSuperAdmin, IsMinistryAdmin, IsAgencyManagerOrAbove,
            CanManageAssets, CanDeleteAssets, CanViewAuditLogs, HasMinistrySchema,
        )

        self.super_admin = UserModel.objects.create_user(
            username='super', password='Test@123',
            role='SUPER_ADMIN', ministry_schema=None,
        )
        self.ministry_admin = UserModel.objects.create_user(
            username='admin', password='Test@123',
            role='MINISTRY_ADMIN', ministry_schema='moh_schema',
        )
        self.agency_manager = UserModel.objects.create_user(
            username='manager', password='Test@123',
            role='AGENCY_MANAGER', ministry_schema='moh_schema',
        )
        self.facility_clerk = UserModel.objects.create_user(
            username='clerk', password='Test@123',
            role='FACILITY_CLERK', ministry_schema='moh_schema',
        )
        self.auditor = UserModel.objects.create_user(
            username='auditor', password='Test@123',
            role='AUDITOR', ministry_schema='moh_schema',
        )

        self.permissions = {
            'IsSuperAdmin': IsSuperAdmin,
            'IsMinistryAdmin': IsMinistryAdmin,
            'IsAgencyManagerOrAbove': IsAgencyManagerOrAbove,
            'CanManageAssets': CanManageAssets,
            'CanDeleteAssets': CanDeleteAssets,
            'CanViewAuditLogs': CanViewAuditLogs,
            'HasMinistrySchema': HasMinistrySchema,
        }

    def _mock_request(self, user, method='GET'):
        """Helper: create a mock request with the given user and HTTP method."""
        request = Mock(user=user, method=method)
        return request

    # ── IsSuperAdmin ──────────────────────────────────────────────────────

    def test_is_super_admin_allows_super_admin(self):
        perm = self.permissions['IsSuperAdmin']()
        self.assertTrue(perm.has_permission(self._mock_request(self.super_admin), None))

    def test_is_super_admin_blocks_ministry_admin(self):
        perm = self.permissions['IsSuperAdmin']()
        self.assertFalse(perm.has_permission(self._mock_request(self.ministry_admin), None))

    def test_is_super_admin_blocks_facility_clerk(self):
        perm = self.permissions['IsSuperAdmin']()
        self.assertFalse(perm.has_permission(self._mock_request(self.facility_clerk), None))

    def test_is_super_admin_blocks_anonymous(self):
        perm = self.permissions['IsSuperAdmin']()
        request = Mock(is_authenticated=False)
        self.assertFalse(perm.has_permission(request, None))

    # ── IsMinistryAdmin ───────────────────────────────────────────────────

    def test_ministry_admin_allows_super_admin(self):
        perm = self.permissions['IsMinistryAdmin']()
        self.assertTrue(perm.has_permission(self._mock_request(self.super_admin), None))

    def test_ministry_admin_allows_ministry_admin(self):
        perm = self.permissions['IsMinistryAdmin']()
        self.assertTrue(perm.has_permission(self._mock_request(self.ministry_admin), None))

    def test_ministry_admin_blocks_facility_clerk(self):
        perm = self.permissions['IsMinistryAdmin']()
        self.assertFalse(perm.has_permission(self._mock_request(self.facility_clerk), None))

    # ── Role Hierarchy Tests ──────────────────────────────────────────────

    def test_agency_manager_or_above_allows_super_admin(self):
        perm = self.permissions['IsAgencyManagerOrAbove']()
        self.assertTrue(perm.has_permission(self._mock_request(self.super_admin), None))

    def test_agency_manager_or_above_allows_agency_manager(self):
        perm = self.permissions['IsAgencyManagerOrAbove']()
        self.assertTrue(perm.has_permission(self._mock_request(self.agency_manager), None))

    def test_agency_manager_or_above_blocks_facility_clerk(self):
        perm = self.permissions['IsAgencyManagerOrAbove']()
        self.assertFalse(perm.has_permission(self._mock_request(self.facility_clerk), None))

    # ── CanManageAssets ───────────────────────────────────────────────────

    def test_can_manage_assets_get_allows_auditor(self):
        """All authenticated users should be able to GET assets."""
        perm = self.permissions['CanManageAssets']()
        self.assertTrue(perm.has_permission(self._mock_request(self.auditor, 'GET'), None))

    def test_can_manage_assets_post_blocks_auditor(self):
        """POST should be blocked for AUDITOR (read-only role)."""
        perm = self.permissions['CanManageAssets']()
        self.assertFalse(perm.has_permission(self._mock_request(self.auditor, 'POST'), None))

    def test_can_manage_assets_post_allows_facility_clerk(self):
        """POST should be allowed for FACILITY_CLERK."""
        perm = self.permissions['CanManageAssets']()
        self.assertTrue(perm.has_permission(self._mock_request(self.facility_clerk, 'POST'), None))

    # ── CanDeleteAssets ────────────────────────────────────────────────────

    def test_delete_asset_allows_ministry_admin(self):
        """DELETE should be allowed for MINISTRY_ADMIN."""
        perm = self.permissions['CanDeleteAssets']()
        request = self._mock_request(self.ministry_admin, 'DELETE')
        self.assertTrue(perm.has_permission(request, None))

    def test_delete_asset_blocks_facility_clerk(self):
        """DELETE should be blocked for FACILITY_CLERK."""
        perm = self.permissions['CanDeleteAssets']()
        request = self._mock_request(self.facility_clerk, 'DELETE')
        self.assertFalse(perm.has_permission(request, None))

    def test_delete_asset_get_allows_clerk(self):
        """GET should be allowed regardless of role."""
        perm = self.permissions['CanDeleteAssets']()
        request = self._mock_request(self.facility_clerk, 'GET')
        self.assertTrue(perm.has_permission(request, None))

    # ── CanViewAuditLogs ──────────────────────────────────────────────────

    def test_view_audit_logs_allows_auditor(self):
        perm = self.permissions['CanViewAuditLogs']()
        self.assertTrue(perm.has_permission(self._mock_request(self.auditor), None))

    def test_view_audit_logs_blocks_facility_clerk(self):
        perm = self.permissions['CanViewAuditLogs']()
        self.assertFalse(perm.has_permission(self._mock_request(self.facility_clerk), None))

    # ── HasMinistrySchema ──────────────────────────────────────────────────

    def test_has_ministry_schema_super_admin_exempt(self):
        """SUPER_ADMIN should pass HasMinistrySchema even without a schema."""
        perm = self.permissions['HasMinistrySchema']()
        self.assertTrue(perm.has_permission(self._mock_request(self.super_admin), None))

    def test_has_ministry_schema_blocks_user_without_schema(self):
        """Non-super users without ministry_schema should be blocked."""
        user_no_schema = UserModel.objects.create_user(
            username='orphan', password='Test@123',
            role='FACILITY_CLERK', ministry_schema=None,
        )
        perm = self.permissions['HasMinistrySchema']()
        self.assertFalse(perm.has_permission(self._mock_request(user_no_schema), None))

    def test_has_ministry_schema_allows_user_with_schema(self):
        perm = self.permissions['HasMinistrySchema']()
        self.assertTrue(perm.has_permission(self._mock_request(self.facility_clerk), None))


# =============================================================================
# SuperAdminAuditLog Tamper Protection Tests
# =============================================================================

class SuperAdminAuditLogTamperTest(TestCase):
    """Verify that SuperAdminAuditLog records cannot be modified or deleted."""

    def setUp(self):
        self.log = SuperAdminAuditLog.objects.create(
            performed_by_id=1,
            performed_by_name='Test Admin',
            action='USER_CREATED',
            description='Created test user',
        )

    def test_cannot_update_existing_record(self):
        """Updating an existing SuperAdminAuditLog should raise PermissionError."""
        with self.assertRaises(PermissionError):
            self.log.description = 'Changed description'
            self.log.save()

    def test_cannot_delete_record(self):
        """Deleting a SuperAdminAuditLog should raise PermissionError."""
        with self.assertRaises(PermissionError):
            self.log.delete()
