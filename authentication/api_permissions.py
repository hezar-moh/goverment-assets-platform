# Purpose: DRF permission classes that control who can access each API endpoint.

from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Only SUPER_ADMIN role."""
    message = "Only Super Admin can access this endpoint."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'SUPER_ADMIN'


class IsMinistryAdmin(BasePermission):
    """MINISTRY_ADMIN and above."""
    message = "Ministry Admin or above required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN']


class IsAgencyManagerOrAbove(BasePermission):
    """AGENCY_MANAGER and above."""
    message = "Agency Manager or above required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER']


class CanManageAssets(BasePermission):
    """Allows asset write access. Auditors are read-only."""
    message = "You do not have permission to manage assets."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK']


class CanDeleteAssets(BasePermission):
    """Only MINISTRY_ADMIN and SUPER_ADMIN can DELETE."""
    message = "Only Ministry Admin can delete assets."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method == 'DELETE':
            return request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN']
        return True


class CanViewAuditLogs(BasePermission):
    """AUDITOR, MINISTRY_ADMIN, and SUPER_ADMIN can view audit logs."""
    message = "Auditor or above required to view audit logs."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AUDITOR']


class HasMinistrySchema(BasePermission):
    """Block users without a ministry_schema. SUPER_ADMIN is exempt."""
    message = "Your account is not assigned to any ministry. Contact your administrator."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'SUPER_ADMIN':
            return True
        return bool(request.user.ministry_schema)