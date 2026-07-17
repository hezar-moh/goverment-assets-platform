from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    message = "Only Super Admin can access this endpoint."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'SUPER_ADMIN'


class IsMinistryAdmin(BasePermission):
    message = "Ministry Admin or above required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN']


class IsAgencyManagerOrAbove(BasePermission):
    message = "Agency Manager or above required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER']


class CanManageAssets(BasePermission):
    message = "You do not have permission to manage assets."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK']


class CanDeleteAssets(BasePermission):
    message = "Only Ministry Admin can delete assets."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method == 'DELETE':
            return request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN']
        return True


class CanViewAuditLogs(BasePermission):
    message = "Auditor or above required to view audit logs."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['SUPER_ADMIN', 'MINISTRY_ADMIN', 'AUDITOR']


class HasMinistrySchema(BasePermission):
    message = "Your account is not assigned to any ministry. Contact your administrator."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'SUPER_ADMIN':
            return True
        return bool(request.user.ministry_schema)
