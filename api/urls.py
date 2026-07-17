from django.urls import path
from .auth_views import (LoginAPIView, RefreshTokenAPIView, MeAPIView,
                         VerifyTokenAPIView, LogoutAPIView)
from .asset_views import AssetListCreateAPIView, AssetDetailAPIView, AssetCategoryListAPIView
from .org_views import OrgUnitListAPIView, AuditLogListAPIView, DashboardStatsAPIView

urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('auth/refresh/', RefreshTokenAPIView.as_view(), name='api_refresh'),
    path('auth/me/', MeAPIView.as_view(), name='api_me'),
    path('auth/verify-token/', VerifyTokenAPIView.as_view(), name='api_verify_token'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('assets/categories/', AssetCategoryListAPIView.as_view(), name='api_asset_categories'),
    path('assets/', AssetListCreateAPIView.as_view(), name='api_asset_list'),
    path('assets/<int:asset_id>/', AssetDetailAPIView.as_view(), name='api_asset_detail'),
    path('org-units/', OrgUnitListAPIView.as_view(), name='api_org_units'),
    path('audit-logs/', AuditLogListAPIView.as_view(), name='api_audit_logs'),
    path('dashboard/stats/', DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
]
