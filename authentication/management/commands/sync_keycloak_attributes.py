# Purpose: One-time script to push role + ministry_schema custom attributes to all
#          6 demo users in Keycloak. If users were created manually (via admin console
#          instead of setup_demo_data), they won't have these attributes, and Django's
#          OIDC backend won't know their role/schema on login.


from django.core.management.base import BaseCommand

USERS_DATA = [
    # (username,   role,            ministry_schema)
    ('superadmin', 'SUPER_ADMIN',   ''),
    ('moh_admin',  'MINISTRY_ADMIN', 'moh_schema'),
    ('mnh_manager', 'AGENCY_MANAGER', 'moh_schema'),
    ('rad_clerk',  'FACILITY_CLERK', 'moh_schema'),
    ('moh_auditor', 'AUDITOR',       'moh_schema'),
    ('mof_admin',  'MINISTRY_ADMIN', 'mof_schema'),
]


class Command(BaseCommand):
    help = 'Sync role + ministry_schema attributes to all 6 demo Keycloak users'

    def handle(self, *args, **options):
        from authentication.keycloak_admin import KeycloakAdminService

        kc = KeycloakAdminService()

        kc.ensure_custom_attributes_defined()
        self.stdout.write('  [OK] Realm user profile configured for custom attributes')

        ok = 0
        fail = 0

        for username, role, ministry_schema in USERS_DATA:
            keycloak_id = kc.get_user_id(username)
            if not keycloak_id:
                self.stdout.write(
                    self.style.WARNING(
                        f'  [SKIP] {username}: not found'
                    )
                )
                fail += 1
                continue

            kc.update_user(
                keycloak_id=keycloak_id,
                role=role,
                ministry_schema=ministry_schema,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'  [OK]   {username} => role={role}, schema={ministry_schema!r}'
                )
            )
            ok += 1

        self.stdout.write(f'\nDone. {ok} updated, {fail} skipped.')
