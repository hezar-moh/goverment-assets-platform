"""Unit tests for the organisations app.

Tests the AuditLog tamper-proof protection, OrgUnit hierarchy,
and MasterData model validation.
"""

from django.db import IntegrityError
from django_tenants.test.cases import TenantTestCase
from organizations.models import AuditLog, OrgUnit, MasterData


class OrganizationModelTests(TenantTestCase):
    """AuditLog tamper protection, OrgUnit hierarchy, and MasterData constraints.

    All in one class to create the tenant schema once rather than per-class.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Test Ministry"
        tenant.short_name = "TST"

    @classmethod
    def get_test_schema_name(cls):
        return 'test_org'

    # =========================================================================
    # AuditLog Tamper Protection
    # =========================================================================

    def test_cannot_update_existing_audit_log(self):
        log = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Test User',
            action='CREATE', model_name='Asset',
            object_id='1', object_repr='MOH-ICT-2026-0001',
            ip_address='127.0.0.1',
        )
        log.object_repr = 'Changed value'
        with self.assertRaises(PermissionError):
            log.save()

    def test_cannot_delete_audit_log(self):
        log = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Test User',
            action='CREATE', model_name='Asset',
            object_id='1', object_repr='MOH-ICT-2026-0001',
            ip_address='127.0.0.1',
        )
        with self.assertRaises(PermissionError):
            log.delete()

    def test_can_create_new_audit_log(self):
        AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Test User',
            action='CREATE', model_name='Asset',
            object_id='1', object_repr='MOH-ICT-2026-0001',
            ip_address='127.0.0.1',
        )
        new_log = AuditLog.objects.create(
            performed_by_id=2, performed_by_name='Another User',
            action='LOGIN', model_name='CustomUser',
            object_id='2', object_repr='moh_admin',
        )
        self.assertIsNotNone(new_log.pk)
        self.assertEqual(AuditLog.objects.count(), 2)

    def test_audit_log_retains_original_values_after_modification_attempt(self):
        log = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Test User',
            action='CREATE', model_name='Asset',
            object_id='1', object_repr='MOH-ICT-2026-0001',
            ip_address='127.0.0.1',
        )
        with self.assertRaises(PermissionError):
            log.object_repr = 'Hacked value'
            log.save()
        log.refresh_from_db()
        self.assertEqual(log.object_repr, 'MOH-ICT-2026-0001')

    def test_audit_log_auto_timestamp(self):
        log = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Admin User',
            action='CREATE', model_name='Asset',
            object_id='42', object_repr='Test Asset',
        )
        self.assertIsNotNone(log.timestamp)

    def test_audit_log_ordering(self):
        log1 = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='User',
            action='LOGIN', model_name='CustomUser',
        )
        log2 = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='User',
            action='LOGIN', model_name='CustomUser',
        )
        logs = AuditLog.objects.all()
        self.assertGreater(logs[0].pk, logs[1].pk)

    def test_audit_log_string_representation(self):
        log = AuditLog.objects.create(
            performed_by_id=1, performed_by_name='Admin User',
            action='CREATE', model_name='Asset',
            object_id='42', object_repr='Test Asset',
            old_value=None, new_value={'name': 'Test Asset', 'status': 'ACTIVE'},
            ip_address='10.0.0.1',
        )
        self.assertEqual(str(log), 'CREATE on Asset by Admin User')

    # =========================================================================
    # OrgUnit Hierarchy
    # =========================================================================

    def test_ministry_has_no_parent(self):
        ministry = OrgUnit.objects.create(
            name='Ministry of Health', code='MOH', unit_type='MINISTRY',
        )
        self.assertIsNone(ministry.parent)

    def test_agency_has_parent(self):
        ministry = OrgUnit.objects.create(
            name='Ministry of Health', code='MOH', unit_type='MINISTRY',
        )
        agency = OrgUnit.objects.create(
            name='Muhimbili National Hospital', code='MNH',
            unit_type='AGENCY', parent=ministry,
        )
        self.assertEqual(agency.parent, ministry)

    def test_facility_full_path(self):
        ministry = OrgUnit.objects.create(
            name='Ministry of Health', code='MOH', unit_type='MINISTRY',
        )
        agency = OrgUnit.objects.create(
            name='Muhimbili National Hospital', code='MNH',
            unit_type='AGENCY', parent=ministry,
        )
        facility = OrgUnit.objects.create(
            name='Radiology Department', code='RAD',
            unit_type='FACILITY', parent=agency,
        )
        expected = 'Ministry of Health > Muhimbili National Hospital > Radiology Department'
        self.assertEqual(facility.get_full_path(), expected)

    def test_ministry_full_path(self):
        ministry = OrgUnit.objects.create(
            name='Ministry of Health', code='MOH', unit_type='MINISTRY',
        )
        self.assertEqual(ministry.get_full_path(), 'Ministry of Health')

    def test_org_unit_default_is_active(self):
        org = OrgUnit.objects.create(
            name='Ministry of Health', code='MOH', unit_type='MINISTRY',
        )
        self.assertTrue(org.is_active)

    # =========================================================================
    # MasterData
    # =========================================================================

    def test_master_data_string(self):
        data = MasterData.objects.create(
            category='FUNDING_SOURCE', value='GOVT',
            label='Government Budget', sort_order=1,
        )
        self.assertEqual(str(data), 'FUNDING_SOURCE: Government Budget')

    def test_master_data_unique_together(self):
        MasterData.objects.create(
            category='FUNDING_SOURCE', value='GOVT',
            label='Government Budget', sort_order=1,
        )
        with self.assertRaises(IntegrityError):
            MasterData.objects.create(
                category='FUNDING_SOURCE', value='GOVT', label='Duplicate',
            )

    def test_master_data_default_sort_order(self):
        item = MasterData.objects.create(
            category='FUNDING_SOURCE', value='NEW', label='New Source',
        )
        self.assertEqual(item.sort_order, 0)

    def test_master_data_default_is_active(self):
        data = MasterData.objects.create(
            category='FUNDING_SOURCE', value='GOVT', label='Government Budget',
        )
        self.assertTrue(data.is_active)

    def test_master_data_category_choices(self):
        expected_categories = {
            'FUNDING_SOURCE', 'ACQUISITION_METHOD',
            'LOCATION_TYPE', 'DISPOSAL_METHOD', 'COST_CENTRE',
        }
        actual = {code for code, _ in MasterData.CATEGORY_CHOICES}
        self.assertEqual(actual, expected_categories)
