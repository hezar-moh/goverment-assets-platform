# Purpose: Maps all API URL paths to their view classes for authentication, assets, and organisations.

from django.urls import path

from .api_views import (
    LoginAPIView, RefreshTokenAPIView, MeAPIView,
    VerifyTokenAPIView, LogoutAPIView,
)
from assets.api_views import (
    AssetListCreateAPIView, AssetDetailAPIView, AssetCategoryListAPIView,
)
from organizations.api_views import (
    OrgUnitListAPIView, AuditLogListAPIView, DashboardStatsAPIView,
)

urlpatterns = [
    # Authentication
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('auth/refresh/', RefreshTokenAPIView.as_view(), name='api_refresh'),
    path('auth/me/', MeAPIView.as_view(), name='api_me'),
    path('auth/verify-token/', VerifyTokenAPIView.as_view(), name='api_verify_token'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_logout'),

    # Assets
    path('assets/categories/', AssetCategoryListAPIView.as_view(), name='api_asset_categories'),
    path('assets/', AssetListCreateAPIView.as_view(), name='api_asset_list'),
    path('assets/<int:asset_id>/', AssetDetailAPIView.as_view(), name='api_asset_detail'),

    # Organisation
    path('org-units/', OrgUnitListAPIView.as_view(), name='api_org_units'),

    # Audit logs
    path('audit-logs/', AuditLogListAPIView.as_view(), name='api_audit_logs'),

    # Dashboard statistics
    path('dashboard/stats/', DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
]