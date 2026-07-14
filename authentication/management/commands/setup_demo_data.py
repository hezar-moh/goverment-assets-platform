from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context
from datetime import date, timedelta


class Command(BaseCommand):
    """
    Reset and seed professional demo data for presentations.

    Creates 6 users (Django only or Django + Keycloak), 5 asset categories,
    2 org units, 13 assets, and audit logs across 2 ministries.

    Usage:
        python manage.py setup_demo_data               # full reset + Keycloak sync
        python manage.py setup_demo_data --no-keycloak  # full reset, skip Keycloak
        python manage.py setup_demo_data --clean         # clean only
        python manage.py setup_demo_data --seed          # seed only (no clean)
    """
    help = 'Clean test data and seed professional demo data'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='Only clean existing data')
        parser.add_argument('--seed', action='store_true', help='Only seed demo data (without cleaning)')
        parser.add_argument('--no-keycloak', action='store_true', help='Skip Keycloak user creation')

    def handle(self, *args, **options):
        clean_only = options['clean']
        seed_only  = options['seed']
        self.sync_keycloak = not options['no_keycloak']

        if not seed_only:
            self._clean_data()

        if not clean_only:
            self._seed_data()

        self.stdout.write(
            self.style.SUCCESS('\n[OK] Demo data setup complete!')
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CLEAN
    # ─────────────────────────────────────────────────────────────────────────

    def _clean_data(self):
        self.stdout.write('\nCleaning test data...')

        # Clean tenant schemas first (assets, audit logs)
        from tenants.models import Ministry
        ministries = Ministry.objects.exclude(schema_name='public')

        for ministry in ministries:
            with schema_context(ministry.schema_name):
                from assets.models import Asset
                from organizations.models import AuditLog

                asset_count = Asset.objects.count()
                Asset.objects.all().delete()

                log_count = AuditLog.objects.count()
                AuditLog.admin_bulk_delete()

                self.stdout.write(
                    f'  [OK] Cleared {asset_count} assets + '
                    f'{log_count} logs from {ministry.schema_name}'
                )

        # Clean public schema tables
        from authentication.models import LoginAttempt, PendingAccess

        deleted = LoginAttempt.objects.all().delete()
        self.stdout.write(f'  [OK] Cleared login attempts: {deleted[0]}')

        deleted = PendingAccess.objects.all().delete()
        self.stdout.write(f'  [OK] Cleared pending access: {deleted[0]}')

        # Delete all users — the seed step will recreate the 6 demo users.
        # This guarantees a predictable state after running setup_demo_data.
        from authentication.models import CustomUser
        total_users = CustomUser.objects.count()
        CustomUser.objects.all().delete()
        self.stdout.write(f'  [OK] Deleted {total_users} users (will recreate demo users)')

        self.stdout.write(self.style.SUCCESS('  Cleaning complete.'))

    # ─────────────────────────────────────────────────────────────────────────
    # SEED
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_data(self):
        self.stdout.write('\nSeeding demo data...')
        self._seed_ministries()
        self._run_tenant_migrations()
        self._seed_categories()
        self._seed_org_units()
        self._seed_users()
        self._seed_moh_data()
        self._seed_mof_data()
        self.stdout.write(self.style.SUCCESS('  Seeding complete.'))

    def _run_tenant_migrations(self):
        """Create tables in tenant schemas (required after new ministry creation)."""
        self.stdout.write('  Running tenant migrations...')
        call_command('migrate_schemas', verbosity=0)
        self.stdout.write('  [OK] Tenant migrations complete')

    def _seed_ministries(self):
        """Create ministry schemas if they don't exist (idempotent)."""
        from tenants.models import Ministry, Domain
        ministries_data = [
            {'name': 'Ministry of Health', 'schema_name': 'moh_schema', 'domain': 'moh.localhost'},
            {'name': 'Ministry of Finance', 'schema_name': 'mof_schema', 'domain': 'mof.localhost'},
        ]
        created = 0
        for data in ministries_data:
            ministry, is_new = Ministry.objects.get_or_create(
                schema_name=data['schema_name'],
                defaults={'name': data['name']}
            )
            if is_new:
                Domain.objects.get_or_create(
                    domain=data['domain'],
                    defaults={
                        'tenant': ministry,
                        'is_primary': True,
                    }
                )
                created += 1
        if created:
            self.stdout.write(f'  [OK] Created {created} ministry schemas')
        else:
            self.stdout.write(f'  [OK] Ministries already exist')

    def _seed_categories(self):
        """Create asset categories in every tenant schema (idempotent)."""
        from tenants.models import Ministry
        categories = [
            ('ICT',     'ICT Equipment'),
            ('VEH',     'Vehicle'),
            ('FURN',    'Furniture & Fixtures'),
            ('MEDICAL', 'Medical Equipment'),
            ('LAND',    'Land & Buildings'),
        ]
        schemas = list(
            Ministry.objects.exclude(schema_name='public')
            .values_list('schema_name', flat=True)
        )
        for schema_name in schemas:
            with schema_context(schema_name):
                from assets.models import AssetCategory
                for code, name in categories:
                    AssetCategory.objects.get_or_create(
                        code=code, defaults={'name': name}
                    )
        self.stdout.write(
            f'  [OK] Ensured {len(categories)} categories in {len(schemas)} schemas'
        )

    def _seed_org_units(self):
        """Create org units in each ministry schema (idempotent)."""
        from tenants.models import Ministry
        ministries = Ministry.objects.exclude(schema_name='public')

        for ministry in ministries:
            with schema_context(ministry.schema_name):
                from organizations.models import OrgUnit

                if ministry.schema_name == 'moh_schema':
                    # Get or create ministry-level first (parent for agencies)
                    moh_unit, _ = OrgUnit.objects.get_or_create(
                        code='MOH',
                        defaults={
                            'name': 'Ministry of Health',
                            'unit_type': 'MINISTRY',
                        }
                    )
                    mnh, _ = OrgUnit.objects.get_or_create(
                        code='MNH',
                        defaults={
                            'name': 'Muhimbili National Hospital',
                            'unit_type': 'AGENCY',
                            'parent': moh_unit,
                        }
                    )
                    OrgUnit.objects.get_or_create(
                        code='RAD',
                        defaults={
                            'name': 'Radiology Department',
                            'unit_type': 'FACILITY',
                            'parent': mnh,
                        }
                    )
                elif ministry.schema_name == 'mof_schema':
                    OrgUnit.objects.get_or_create(
                        code='MOF',
                        defaults={
                            'name': 'Ministry of Finance',
                            'unit_type': 'MINISTRY',
                        }
                    )

        self.stdout.write('  [OK] Ensured org units exist in each schema')

    def _seed_users(self):
        """Create demo users in Django (and optionally Keycloak)."""
        from authentication.models import CustomUser

        users_data = [
            {
                'username': 'superadmin',
                'password': 'Admin@123',
                'email': 'superadmin@platform.go.tz',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'SUPER_ADMIN',
                'ministry_schema': None,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'moh_admin',
                'password': 'Admin@123',
                'email': 'amina@moh.go.tz',
                'first_name': 'Amina',
                'last_name': 'Hassan',
                'role': 'MINISTRY_ADMIN',
                'ministry_schema': 'moh_schema',
            },
            {
                'username': 'mnh_manager',
                'password': 'Admin@123',
                'email': 'john.mwangi@moh.go.tz',
                'first_name': 'John',
                'last_name': 'Mwangi',
                'role': 'AGENCY_MANAGER',
                'ministry_schema': 'moh_schema',
            },
            {
                'username': 'rad_clerk',
                'password': 'Admin@123',
                'email': 'asha.salum@moh.go.tz',
                'first_name': 'Asha',
                'last_name': 'Salum',
                'role': 'FACILITY_CLERK',
                'ministry_schema': 'moh_schema',
            },
            {
                'username': 'moh_auditor',
                'password': 'Admin@123',
                'email': 'david.mushi@moh.go.tz',
                'first_name': 'David',
                'last_name': 'Mushi',
                'role': 'AUDITOR',
                'ministry_schema': 'moh_schema',
            },
            {
                'username': 'mof_admin',
                'password': 'Admin@123',
                'email': 'grace@mof.go.tz',
                'first_name': 'Grace',
                'last_name': 'Mbwilo',
                'role': 'MINISTRY_ADMIN',
                'ministry_schema': 'mof_schema',
            },
        ]

        # Delete existing demo users so IDs reset cleanly each run
        demo_usernames = [u['username'] for u in users_data]
        CustomUser.objects.filter(username__in=demo_usernames).delete()

        for info in users_data:
            password = info.pop('password')
            keycloak_id = None

            # Create in Keycloak first (if enabled)
            if self.sync_keycloak:
                try:
                    from authentication.keycloak_admin import KeycloakAdminService
                    kc = KeycloakAdminService()
                    kc.ensure_custom_attributes_defined()
                    # Delete existing Keycloak user first to avoid 409 conflict
                    existing_id = kc.get_user_id(info['username'])
                    if existing_id:
                        kc.delete_user(existing_id)
                    keycloak_id = kc.create_user(
                        username=info['username'],
                        email=info.get('email', ''),
                        first_name=info.get('first_name', ''),
                        last_name=info.get('last_name', ''),
                        password=password,
                        role=info['role'],
                        ministry_schema=info.get('ministry_schema', '') or '',
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Warning: Keycloak sync failed for '
                            f'{info["username"]}: {e}'
                        )
                    )

            user = CustomUser(**info, keycloak_id=keycloak_id)
            user.set_password(password)
            user.save()
            kc_status = ' + Keycloak' if keycloak_id else ''
            self.stdout.write(
                f'  [OK] Created user: {user.username}{kc_status}'
            )

    def _seed_moh_data(self):
        self.stdout.write('\n  Seeding Ministry of Health (moh_schema)...')

        with schema_context('moh_schema'):
            from assets.models import Asset, AssetCategory
            from organizations.models import AuditLog, OrgUnit

            today = date.today()
            ict  = AssetCategory.objects.get(code='ICT')
            veh  = AssetCategory.objects.get(code='VEH')
            furn = AssetCategory.objects.get(code='FURN')
            med  = AssetCategory.objects.get(code='MEDICAL')

            mnh = OrgUnit.objects.filter(unit_type='AGENCY').first()
            rad = OrgUnit.objects.filter(unit_type='FACILITY').first()

            Asset.objects.create(
                asset_number='MOH-ICT-2025-0001',
                name='Dell Laptop Latitude 5540',
                category=ict,
                serial_number='DLLAT5540-TZ-001',
                manufacturer='Dell Technologies',
                model_number='Latitude 5540',
                supplier_name='Computer World Tanzania Ltd',
                purchase_order_number='PO-MOH-2025-0234',
                status='ACTIVE',
                condition='EXCELLENT',
                location_type='OFFICE',
                location_description='Ministry HQ Block A Room 201',
                org_unit_id=mnh.id if mnh else None,
                org_unit_name=mnh.name if mnh else '',
                acquisition_date=date(2025, 3, 15),
                warranty_expiry_date=date(2028, 3, 15),
                asset_expiry_date=date(2030, 3, 15),
                useful_life_years=5,
                acquisition_cost=2850000.00,
                current_value=2500000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='ICT Department',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-ICT-2025-0002',
                name='HP LaserJet Pro M428fdw Printer',
                category=ict,
                serial_number='HPLJ428-TZ-002',
                manufacturer='HP Inc',
                model_number='LaserJet Pro M428fdw',
                supplier_name='Office Solutions Tanzania',
                purchase_order_number='PO-MOH-2025-0235',
                status='ACTIVE',
                condition='GOOD',
                location_type='OFFICE',
                location_description='Ministry HQ Block A Room 201',
                org_unit_id=mnh.id if mnh else None,
                org_unit_name=mnh.name if mnh else '',
                acquisition_date=date(2025, 3, 15),
                warranty_expiry_date=date(2027, 3, 15),
                asset_expiry_date=date(2030, 3, 15),
                useful_life_years=5,
                acquisition_cost=850000.00,
                current_value=800000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='ICT Department',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-ICT-2025-0003',
                name='Cisco Catalyst 2960 Network Switch',
                category=ict,
                serial_number='CISCO2960-TZ-003',
                manufacturer='Cisco Systems',
                model_number='Catalyst 2960-48TT-L',
                supplier_name='Techno Africa Ltd',
                purchase_order_number='PO-MOH-2025-0240',
                status='ACTIVE',
                condition='GOOD',
                location_type='OFFICE',
                location_description='Server Room Block B',
                acquisition_date=date(2024, 6, 10),
                warranty_expiry_date=date(2027, 6, 10),
                asset_expiry_date=date(2029, 6, 10),
                useful_life_years=5,
                acquisition_cost=3200000.00,
                current_value=2800000.00,
                funding_source='World Bank Grant',
                acquisition_method='Direct Procurement',
                cost_centre='ICT Department',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-ICT-2024-0001',
                name='Samsung 65" Smart TV Meeting Room Display',
                category=ict,
                serial_number='SAM65S-TZ-001',
                manufacturer='Samsung Electronics',
                model_number='UA65TU7000',
                supplier_name='Electronics Hub Tanzania',
                status='ACTIVE',
                condition='GOOD',
                location_type='OFFICE',
                location_description='Board Room Floor 3',
                acquisition_date=date(2024, 1, 20),
                warranty_expiry_date=date(2026, 1, 20),
                asset_expiry_date=date(2034, 1, 20),
                useful_life_years=10,
                acquisition_cost=1800000.00,
                current_value=1500000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='Administration',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-VEH-2023-0001',
                name='Toyota Land Cruiser Prado 150',
                category=veh,
                serial_number='JTEBU5JR3G5122456',
                manufacturer='Toyota Motor Corporation',
                model_number='Land Cruiser Prado 150 Series',
                supplier_name='Toyota Tanzania Ltd',
                purchase_order_number='PO-MOH-2023-0089',
                status='ACTIVE',
                condition='GOOD',
                location_type='FIELD',
                location_description='Ministerial Vehicle Pool',
                acquisition_date=date(2023, 7, 1),
                warranty_expiry_date=date(2026, 7, 1),
                asset_expiry_date=date(2033, 7, 1),
                useful_life_years=10,
                acquisition_cost=85000000.00,
                current_value=72000000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='Transport Department',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-VEH-2022-0001',
                name='Toyota Hiace Ambulance',
                category=veh,
                serial_number='JTFSS22P8C0012345',
                manufacturer='Toyota Motor Corporation',
                model_number='Hiace High Roof',
                supplier_name='Toyota Tanzania Ltd',
                status='UNDER_MAINTENANCE',
                condition='FAIR',
                location_type='WORKSHOP',
                location_description='TMDA Workshop Dar es Salaam',
                acquisition_date=date(2022, 3, 15),
                warranty_expiry_date=date(2024, 3, 15),
                asset_expiry_date=date(2032, 3, 15),
                useful_life_years=10,
                acquisition_cost=65000000.00,
                current_value=45000000.00,
                funding_source='USAID Grant',
                acquisition_method='Donation',
                cost_centre='Emergency Services',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            Asset.objects.create(
                asset_number='MOH-MED-2024-0001',
                name='Mindray BC-5300 Auto Haematology Analyzer',
                category=med,
                serial_number='MR-BC5300-TZ-001',
                manufacturer='Mindray Medical International',
                model_number='BC-5300',
                supplier_name='Medical Supplies Africa Ltd',
                purchase_order_number='PO-MOH-2024-0456',
                status='ACTIVE',
                condition='EXCELLENT',
                location_type='HOSPITAL',
                location_description='MNH Laboratory Block C',
                org_unit_id=rad.id if rad else None,
                org_unit_name=rad.name if rad else '',
                acquisition_date=date(2024, 9, 1),
                warranty_expiry_date=date(2026, 9, 1),
                asset_expiry_date=date(today.year + 1, 1, 1),
                useful_life_years=8,
                acquisition_cost=45000000.00,
                current_value=42000000.00,
                funding_source='World Bank Grant',
                acquisition_method='Tender',
                cost_centre='Laboratory Services',
                registered_by_id=3,
                registered_by_name='John Mwangi',
            )

            Asset.objects.create(
                asset_number='MOH-MED-2023-0001',
                name='Philips IntelliVue MX750 Patient Monitor',
                category=med,
                serial_number='PH-MX750-TZ-001',
                manufacturer='Philips Healthcare',
                model_number='IntelliVue MX750',
                supplier_name='Philips East Africa',
                status='ACTIVE',
                condition='GOOD',
                location_type='HOSPITAL',
                location_description='MNH ICU Ward 4',
                org_unit_id=rad.id if rad else None,
                org_unit_name=rad.name if rad else '',
                acquisition_date=date(2023, 11, 15),
                warranty_expiry_date=date(2025, 11, 15),
                asset_expiry_date=date(2033, 11, 15),
                useful_life_years=10,
                acquisition_cost=38000000.00,
                current_value=32000000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='ICU Department',
                registered_by_id=3,
                registered_by_name='John Mwangi',
            )

            Asset.objects.create(
                asset_number='MOH-FURN-2025-0001',
                name='Executive Office Desk Set (8 Pieces)',
                category=furn,
                serial_number='DESK-SET-TZ-001',
                manufacturer='Office Furniture Tanzania',
                model_number='Executive Pro Series',
                supplier_name='Office Furniture Tanzania Ltd',
                status='ACTIVE',
                condition='EXCELLENT',
                location_type='OFFICE',
                location_description='Director General Office Block A Floor 4',
                acquisition_date=date(2025, 1, 10),
                asset_expiry_date=date(2040, 1, 10),
                useful_life_years=15,
                acquisition_cost=4500000.00,
                current_value=4500000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='Administration',
                registered_by_id=2,
                registered_by_name='Amina Hassan',
            )

            self._create_demo_audit_logs('moh_schema')

            count = Asset.objects.count()
            self.stdout.write(f'  [OK] Created {count} MOH assets')

    def _seed_mof_data(self):
        self.stdout.write('\n  Seeding Ministry of Finance (mof_schema)...')

        with schema_context('mof_schema'):
            from assets.models import Asset, AssetCategory

            ict  = AssetCategory.objects.get(code='ICT')
            furn = AssetCategory.objects.get(code='FURN')
            veh  = AssetCategory.objects.get(code='VEH')

            Asset.objects.create(
                asset_number='MOF-ICT-2025-0001',
                name='HP EliteBook 850 G9 Laptop',
                category=ict,
                serial_number='HPEB850-MOF-001',
                manufacturer='HP Inc',
                model_number='EliteBook 850 G9',
                supplier_name='ICT Solutions Tanzania Ltd',
                purchase_order_number='PO-MOF-2025-0112',
                status='ACTIVE',
                condition='EXCELLENT',
                location_type='OFFICE',
                location_description='Finance HQ Block C Room 105',
                acquisition_date=date(2025, 2, 1),
                warranty_expiry_date=date(2028, 2, 1),
                asset_expiry_date=date(2030, 2, 1),
                useful_life_years=5,
                acquisition_cost=3100000.00,
                current_value=3000000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='ICT Department',
                registered_by_id=6,
                registered_by_name='Grace Mbwilo',
            )

            Asset.objects.create(
                asset_number='MOF-ICT-2024-0001',
                name='Lenovo ThinkCentre M90n Desktop Computer',
                category=ict,
                serial_number='LNTC-M90N-MOF-001',
                manufacturer='Lenovo Group',
                model_number='ThinkCentre M90n',
                supplier_name='ICT Solutions Tanzania Ltd',
                status='ACTIVE',
                condition='GOOD',
                location_type='OFFICE',
                location_description='Revenue Department Floor 2',
                acquisition_date=date(2024, 4, 20),
                warranty_expiry_date=date(2027, 4, 20),
                asset_expiry_date=date(2029, 4, 20),
                useful_life_years=5,
                acquisition_cost=1950000.00,
                current_value=1700000.00,
                funding_source='Government Budget',
                acquisition_method='Direct Procurement',
                cost_centre='Revenue Department',
                registered_by_id=6,
                registered_by_name='Grace Mbwilo',
            )

            Asset.objects.create(
                asset_number='MOF-VEH-2023-0001',
                name='Toyota Fortuner 2.8 GD-6 4x4',
                category=veh,
                serial_number='MR0GX3FW9N4012345',
                manufacturer='Toyota Motor Corporation',
                model_number='Fortuner 2.8 GD-6',
                supplier_name='Toyota Tanzania Ltd',
                status='ACTIVE',
                condition='GOOD',
                location_type='FIELD',
                location_description='Ministry Vehicle Pool',
                acquisition_date=date(2023, 9, 15),
                warranty_expiry_date=date(2026, 9, 15),
                asset_expiry_date=date(2033, 9, 15),
                useful_life_years=10,
                acquisition_cost=78000000.00,
                current_value=68000000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='Transport',
                registered_by_id=6,
                registered_by_name='Grace Mbwilo',
            )

            Asset.objects.create(
                asset_number='MOF-FURN-2024-0001',
                name='Conference Room Furniture Set',
                category=furn,
                serial_number='CONF-SET-MOF-001',
                manufacturer='Modern Furniture Co',
                status='ACTIVE',
                condition='EXCELLENT',
                location_type='OFFICE',
                location_description='Conference Room Floor 4',
                acquisition_date=date(2024, 7, 1),
                asset_expiry_date=date(2039, 7, 1),
                useful_life_years=15,
                acquisition_cost=6200000.00,
                current_value=6200000.00,
                funding_source='Government Budget',
                acquisition_method='Tender',
                cost_centre='Administration',
                registered_by_id=6,
                registered_by_name='Grace Mbwilo',
            )

            self._create_demo_audit_logs('mof_schema')

            count = Asset.objects.count()
            self.stdout.write(f'  [OK] Created {count} MOF assets')

    def _create_demo_audit_logs(self, schema_name):
        with schema_context(schema_name):
            from organizations.models import AuditLog

            is_moh = 'moh' in schema_name
            reviewer_id = 3 if is_moh else 6
            reviewer_name = 'John Mwangi' if is_moh else 'Grace Mbwilo'
            admin_id = 2 if is_moh else 6
            admin_name = 'Amina Hassan' if is_moh else 'Grace Mbwilo'
            prefix = schema_name[:3].upper()

            logs = [
                {
                    'performed_by_id': admin_id,
                    'performed_by_name': admin_name,
                    'action': 'LOGIN',
                    'model_name': 'CustomUser',
                    'object_id': str(admin_id),
                    'object_repr': 'moh_admin' if is_moh else 'mof_admin',
                    'ip_address': '192.168.100.18',
                },
                {
                    'performed_by_id': admin_id,
                    'performed_by_name': admin_name,
                    'action': 'CREATE',
                    'model_name': 'Asset',
                    'object_id': '1',
                    'object_repr': f'{prefix}-ICT-2025-0001',
                    'ip_address': '192.168.100.18',
                },
                {
                    'performed_by_id': reviewer_id,
                    'performed_by_name': reviewer_name,
                    'action': 'UPDATE',
                    'model_name': 'Asset',
                    'object_id': '1',
                    'object_repr': 'Updated condition to GOOD',
                    'ip_address': '192.168.100.18',
                },
            ]

            for log_data in logs:
                AuditLog.objects.create(**log_data)
