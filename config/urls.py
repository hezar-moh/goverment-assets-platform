"""URL configuration for the GovAsset platform."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from authentication.views import login_view, logout_view
from authentication.unlock_views import account_unlock_view
from authentication.dashboard_views import dashboard_view
from authentication.user_views import (
    user_list_view,
    user_create_view,
    user_edit_view,
    user_toggle_active_view,
    user_reset_password_view,
    user_sync_from_keycloak_view,
)
from authentication.pending_access_views import (
    pending_access_list_view,
    pending_access_review_view,
    pending_access_clear_view,
)
from assets.views import (
    asset_list_view,
    asset_create_view,
    asset_detail_view,
    asset_edit_view,
    asset_delete_view,
)
from organizations.views import (
    audit_log_detail_view,
    audit_log_view,
    org_unit_list_view,
    org_unit_create_view,
    org_unit_edit_view,
    org_unit_delete_view,
)
from organizations.master_data_views import (
    master_data_list_view,
    master_data_create_view,
    master_data_edit_view,
    master_data_delete_view,
    master_data_seed_view,
    asset_category_list_view,
    asset_category_create_view,
    asset_category_edit_view,
)
from tenants.views import (
    ministry_list_view,
    ministry_create_view,
    ministry_detail_view,
    ministry_toggle_active_view,
)

# Swagger/OpenAPI schema view

schema_view = get_schema_view(
    openapi.Info(
        title="GovAsset Platform API",
        default_version='v1',
        description=(
            "REST API for the Government Asset Management Platform.\n\n"
            "## How to authenticate\n"
            "1. Call POST /api/auth/login/ with username and password\n"
            "2. Copy the 'access' token from the response\n"
            "3. Click the Authorize button and enter: Bearer {your_token}\n"
            "4. All requests will now include the token automatically\n\n"
            "## For Groups 2-10\n"
            "Call GET /api/auth/verify-token/ with the user's Bearer token "
            "to validate it and get role and ministry_schema."
        ),
        contact=openapi.Contact(email="admin@platform.go.tz"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    # Tell Swagger that our API uses JWT Bearer tokens
    authentication_classes=[],
)


urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Web authentication
    path('login/',   login_view,   name='login'),
    path('logout/',  logout_view,  name='logout'),

    # Dashboard
    path('',          dashboard_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # Assets
    path('assets/',                    asset_list_view,   name='asset_list'),
    path('assets/create/',             asset_create_view, name='asset_create'),
    path('assets/<int:asset_id>/',     asset_detail_view, name='asset_detail'),
    path('assets/<int:asset_id>/edit/',   asset_edit_view,   name='asset_edit'),
    path('assets/<int:asset_id>/delete/', asset_delete_view, name='asset_delete'),

    # Users
    path('users/',                          user_list_view,          name='user_list'),
    path('users/create/',                   user_create_view,        name='user_create'),
    path('users/<int:user_id>/edit/',       user_edit_view,          name='user_edit'),
    path('users/<int:user_id>/toggle-active/', user_toggle_active_view, name='user_toggle_active'),
    path('users/<int:user_id>/sync-from-keycloak/', user_sync_from_keycloak_view, name='user_sync_from_keycloak'),
    path('users/<int:user_id>/reset-password/', user_reset_password_view, name='user_reset_password'),

    # Pending access
    path('pending-access/',                       pending_access_list_view,   name='pending_access_list'),
    path('pending-access/<int:request_id>/review/', pending_access_review_view, name='pending_access_review'),
    path('pending-access/clear/',                 pending_access_clear_view,  name='pending_access_clear'),

    # Audit logs
    path('audit-logs/', audit_log_view, name='audit_log'),
    path('audit-log/<int:log_id>/', audit_log_detail_view, name='audit_log_detail'),

    # Organisation
    path('organisation/',                      org_unit_list_view,   name='org_unit_list'),
    path('organisation/create/',               org_unit_create_view, name='org_unit_create'),
    path('organisation/<int:unit_id>/edit/',   org_unit_edit_view,   name='org_unit_edit'),
    path('organisation/<int:unit_id>/delete/', org_unit_delete_view, name='org_unit_delete'),
    

    # Master data
    path('master-data/',                        master_data_list_view,   name='master_data_list'),
    path('master-data/create/',                 master_data_create_view, name='master_data_create'),
    path('master-data/<int:item_id>/edit/',     master_data_edit_view,   name='master_data_edit'),
    path('master-data/<int:item_id>/delete/',   master_data_delete_view, name='master_data_delete'),
    path('master-data/seed/',                   master_data_seed_view,   name='master_data_seed'),
    path('master-data/categories/',             asset_category_list_view,   name='asset_category_list'),
    path('master-data/categories/create/',      asset_category_create_view, name='asset_category_create'),
    path('master-data/categories/<int:category_id>/edit/', asset_category_edit_view, name='asset_category_edit'),

    # Ministries
    path('ministries/',                        ministry_list_view,          name='ministry_list'),
    path('ministries/create/',                 ministry_create_view,        name='ministry_create'),
    path('ministries/<int:ministry_id>/',      ministry_detail_view,        name='ministry_detail'),
    path('ministries/<int:ministry_id>/toggle/', ministry_toggle_active_view, name='ministry_toggle_active'),

    # REST API
    path('api/', include('authentication.api_urls')),

    # Account unlock (from email link)
    path('unlock-account/<uuid:token>/',
         account_unlock_view,
         name='account_unlock'),

    # Keycloak SSO
    path('oidc/', include('mozilla_django_oidc.urls')),

    # API documentation — Swagger UI and ReDoc
    path(
        'api/docs/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    path(
        'api/redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )