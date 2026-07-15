"""Unit tests for the assets app.

Tests the Asset model properties (is_expired, expires_soon, days_until_expiry),
auto-generated asset numbering, and AssetCategory model.
"""

from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from assets.models import Asset, AssetCategory


class AssetModelTests(TenantTestCase):
    """Verify AssetCategory, Asset expiry properties, numbering, and string repr.

    All in one class to create the tenant schema once rather than per-class.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Test Ministry"
        tenant.short_name = "TST"

    @classmethod
    def get_test_schema_name(cls):
        return 'test_assets'

    # ── AssetCategory ───────────────────────────────────────────────────────

    def test_category_string(self):
        """String representation should include code and name."""
        category = AssetCategory.objects.create(
            name='ICT Equipment', code='ICT',
            description='Computers, printers, and networking hardware',
        )
        self.assertEqual(str(category), 'ICT — ICT Equipment')

    def test_category_default_is_active(self):
        """New categories should be active by default."""
        category = AssetCategory.objects.create(name='ICT Equipment', code='ICT')
        self.assertTrue(category.is_active)

    # ── Expiry properties ──────────────────────────────────────────────────

    def _create_asset(self, expiry_date):
        category = AssetCategory.objects.create(name='Test', code='TST')
        return Asset.objects.create(
            asset_number='TST-TST-2026-0001',
            name='Test Asset',
            category=category,
            asset_expiry_date=expiry_date,
            status='ACTIVE',
        )

    def test_is_expired_true_when_date_in_past(self):
        asset = self._create_asset(timezone.now().date() - timedelta(days=1))
        self.assertTrue(asset.is_expired)

    def test_is_expired_false_when_date_in_future(self):
        asset = self._create_asset(timezone.now().date() + timedelta(days=1))
        self.assertFalse(asset.is_expired)

    def test_is_expired_false_when_no_date(self):
        asset = self._create_asset(None)
        self.assertFalse(asset.is_expired)

    def test_is_expired_false_when_expires_today(self):
        asset = self._create_asset(timezone.now().date())
        self.assertFalse(asset.is_expired)

    def test_expires_soon_true_within_90_days(self):
        asset = self._create_asset(timezone.now().date() + timedelta(days=30))
        self.assertTrue(asset.expires_soon)

    def test_expires_soon_false_beyond_90_days(self):
        asset = self._create_asset(timezone.now().date() + timedelta(days=91))
        self.assertFalse(asset.expires_soon)

    def test_expires_soon_false_when_already_expired(self):
        asset = self._create_asset(timezone.now().date() - timedelta(days=1))
        self.assertFalse(asset.expires_soon)

    def test_expires_soon_false_when_no_date(self):
        asset = self._create_asset(None)
        self.assertFalse(asset.expires_soon)

    def test_days_until_expiry_positive(self):
        asset = self._create_asset(timezone.now().date() + timedelta(days=10))
        self.assertEqual(asset.days_until_expiry, 10)

    def test_days_until_expiry_negative_when_expired(self):
        asset = self._create_asset(timezone.now().date() - timedelta(days=5))
        self.assertEqual(asset.days_until_expiry, -5)

    def test_days_until_expiry_none_when_no_date(self):
        asset = self._create_asset(None)
        self.assertIsNone(asset.days_until_expiry)

    def test_warranty_active_when_future(self):
        asset = self._create_asset(timezone.now().date())
        asset.warranty_expiry_date = timezone.now().date() + timedelta(days=30)
        self.assertTrue(asset.warranty_is_active)

    def test_warranty_inactive_when_past(self):
        asset = self._create_asset(timezone.now().date())
        asset.warranty_expiry_date = timezone.now().date() - timedelta(days=1)
        self.assertFalse(asset.warranty_is_active)

    def test_warranty_no_date(self):
        asset = self._create_asset(timezone.now().date())
        asset.warranty_expiry_date = None
        self.assertFalse(asset.warranty_is_active)

    # ── Asset numbering ────────────────────────────────────────────────────

    def test_first_asset_number_starts_at_0001(self):
        from assets.views import generate_asset_number
        AssetCategory.objects.create(name='ICT', code='ICT')
        prefix = self.tenant.schema_name.replace("_schema", "").upper()[:3]
        number = generate_asset_number(self.tenant.schema_name, 'ICT')
        self.assertRegex(number, rf'^{prefix}-ICT-\d{{4}}-0001$')

    def test_asset_number_increments(self):
        from assets.views import generate_asset_number
        category = AssetCategory.objects.create(name='ICT', code='ICT')
        prefix = self.tenant.schema_name.replace("_schema", "").upper()[:3]
        Asset.objects.create(
            asset_number=f'{prefix}-ICT-2026-0001',
            name='Asset 1', category=category,
        )
        number = generate_asset_number(self.tenant.schema_name, 'ICT')
        self.assertIn('0002', number)

    # ── String representation ──────────────────────────────────────────────

    def test_asset_string_representation(self):
        category = AssetCategory.objects.create(name='Test', code='TST')
        asset = Asset.objects.create(
            asset_number='TST-TST-2026-0001',
            name='Office Chair', category=category,
        )
        self.assertEqual(str(asset), 'TST-TST-2026-0001 — Office Chair')


class AssetSchemaIndependentTests(TestCase):
    """Tests that don't need a tenant schema (model meta, choices)."""

    def test_valid_statuses(self):
        expected = {'PLANNED', 'ACTIVE', 'UNDER_MAINTENANCE', 'DECOMMISSIONED', 'DISPOSED'}
        actual = {code for code, _ in Asset.STATUS_CHOICES}
        self.assertEqual(actual, expected)

    def test_default_status(self):
        field = Asset._meta.get_field('status')
        self.assertEqual(field.default, 'ACTIVE')
