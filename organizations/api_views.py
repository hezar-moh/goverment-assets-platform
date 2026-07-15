"""REST API views for organisations, audit logs, and dashboard stats."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django_tenants.utils import schema_context
import logging

from authentication.api_permissions import (
    HasMinistrySchema,
    CanViewAuditLogs,
)
from authentication.api_serializers import (
    AuditLogSerializer,
)

logger = logging.getLogger('authentication')


class OrgUnitListAPIView(APIView):
    """GET /api/org-units/ — Returns the full org hierarchy tree for the user's ministry, plus a flat facilities list for asset registration dropdowns."""

    permission_classes = [IsAuthenticated, HasMinistrySchema]

    def get(self, request):
        user = request.user

        if user.role == 'SUPER_ADMIN':
            return Response({
                'message': (
                    'Super Admin operates at platform level. '
                    'Log in as a ministry user to view org units.'
                ),
                'ministry': None,
            })

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import OrgUnit

                all_units = list(
                    OrgUnit.objects.filter(
                        is_active=True
                    ).order_by('unit_type', 'name')
                )

                ministry_unit = next(
                    (u for u in all_units if u.unit_type == 'MINISTRY'),
                    None
                )

                if not ministry_unit:
                    return Response({
                        'ministry': None,
                        'message':  'No organisation units found.',
                    })

                agencies = [
                    u for u in all_units
                    if u.unit_type == 'AGENCY' and
                    u.parent_id == ministry_unit.id
                ]

                agency_nodes = []
                for agency in agencies:
                    facilities = [
                        u for u in all_units
                        if u.unit_type == 'FACILITY' and
                        u.parent_id == agency.id
                    ]

                    agency_nodes.append({
                        'id':         agency.id,
                        'name':       agency.name,
                        'code':       agency.code or '',
                        'unit_type':  agency.unit_type,
                        'parent_id':  agency.parent_id,
                        'is_active':  agency.is_active,
                        'facilities': [
                            {
                                'id':        f.id,
                                'name':      f.name,
                                'code':      f.code or '',
                                'unit_type': f.unit_type,
                                'parent_id': f.parent_id,
                                'is_active': f.is_active,
                            }
                            for f in facilities
                        ],
                    })

                # Flat facilities list for Flutter asset registration dropdown
                all_facilities = [
                    {
                        'id':        u.id,
                        'name':      u.name,
                        'code':      u.code or '',
                        'unit_type': u.unit_type,
                        'parent_id': u.parent_id,
                    }
                    for u in all_units
                    if u.unit_type == 'FACILITY'
                ]

            return Response({
                'ministry': {
                    'id':       ministry_unit.id,
                    'name':     ministry_unit.name,
                    'code':     ministry_unit.code or '',
                    'unit_type': ministry_unit.unit_type,
                    'agencies': agency_nodes,
                },
                'facilities_flat': all_facilities,
                'total_units': len(all_units),
            })

        except Exception as e:
            logger.error(f"OrgUnit API error: {e}")
            return Response({
                'error':   True,
                'message': f'Error loading org units: {str(e)}',
                'code':    'server_error',
                'status':  500,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuditLogListAPIView(APIView):
    """GET /api/audit-logs/ — Paginated audit logs for the user's ministry. Supports ?action=, ?model=, and ?page= filters."""

    permission_classes = [
        IsAuthenticated,
        HasMinistrySchema,
        CanViewAuditLogs,
    ]

    def get(self, request):
        user = request.user

        if user.role == 'SUPER_ADMIN':
            return Response({
                'message': (
                    'Audit logs are per ministry. '
                    'Log in as a ministry user to view logs.'
                ),
                'count':   0,
                'results': [],
            })

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import AuditLog

                qs = AuditLog.objects.all()

                action_filter = request.GET.get('action', '').strip()
                if action_filter:
                    qs = qs.filter(action=action_filter)

                model_filter = request.GET.get('model', '').strip()
                if model_filter:
                    qs = qs.filter(model_name__icontains=model_filter)

                total = qs.count()

                page_size = 25
                try:
                    page = int(request.GET.get('page', 1))
                    if page < 1:
                        page = 1
                except ValueError:
                    page = 1

                start = (page - 1) * page_size
                end   = start + page_size
                logs  = list(qs[start:end])

            serializer  = AuditLogSerializer(logs, many=True)
            total_pages = (total + page_size - 1) // page_size

            return Response({
                'count':        total,
                'current_page': page,
                'total_pages':  total_pages,
                'page_size':    page_size,
                'results':      serializer.data,
            })

        except Exception as e:
            logger.error(f"AuditLog API error: {e}")
            return Response({
                'error':   True,
                'message': f'Error loading audit logs: {str(e)}',
                'code':    'server_error',
                'status':  500,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DashboardStatsAPIView(APIView):
    """GET /api/dashboard/stats/ — Dashboard statistics for Flutter mobile app (total assets, expiry warnings, recent audit activity)."""

    permission_classes = [IsAuthenticated, HasMinistrySchema]

    def get(self, request):
        user = request.user

        if user.role == 'SUPER_ADMIN':
            try:
                from tenants.models import Ministry
                from authentication.models import CustomUser
                from assets.models import Asset

                total_ministries = Ministry.objects.exclude(
                    schema_name='public'
                ).count()
                total_users = CustomUser.objects.count()

                total_assets  = 0
                active_assets = 0
                for ministry in Ministry.objects.exclude(
                    schema_name='public'
                ):
                    try:
                        with schema_context(ministry.schema_name):
                            total_assets  += Asset.objects.count()
                            active_assets += Asset.objects.filter(
                                status='ACTIVE'
                            ).count()
                    except Exception:
                        pass

                return Response({
                    'role':               'SUPER_ADMIN',
                    'total_ministries':   total_ministries,
                    'total_users':        total_users,
                    'total_assets':       total_assets,
                    'active_assets':      active_assets,
                    'total_warnings':     0,
                    'expired_assets':     [],
                    'expiring_soon':      [],
                })
            except Exception as e:
                return Response({
                    'error':   True,
                    'message': str(e),
                    'code':    'server_error',
                    'status':  500,
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.utils import timezone
        today = timezone.now().date()

        try:
            with schema_context(user.ministry_schema):
                from assets.models import Asset
                from organizations.models import AuditLog

                total_assets  = Asset.objects.count()
                active_assets = Asset.objects.filter(
                    status='ACTIVE'
                ).count()
                total_audit   = AuditLog.objects.count()

                expirable = Asset.objects.filter(
                    asset_expiry_date__isnull=False,
                    status__in=['ACTIVE', 'PLANNED', 'UNDER_MAINTENANCE'],
                ).select_related('category').order_by(
                    'asset_expiry_date'
                )

                expired_list    = []
                expiring_soon   = []
                expiring_later  = []

                from authentication.api_serializers import AssetSerializer
                for asset in expirable:
                    days_left = (
                        asset.asset_expiry_date - today
                    ).days
                    asset_data = {
                        'id':               asset.id,
                        'asset_number':     asset.asset_number,
                        'name':             asset.name,
                        'asset_expiry_date': str(
                            asset.asset_expiry_date
                        ),
                        'days_until_expiry': days_left,
                        'category_name': (
                            asset.category.name
                            if asset.category else ''
                        ),
                    }
                    if days_left < 0:
                        expired_list.append(asset_data)
                    elif days_left <= 30:
                        expiring_soon.append(asset_data)
                    elif days_left <= 90:
                        expiring_later.append(asset_data)

                recent_audit = list(
                    AuditLog.objects.order_by('-timestamp')[:5].values(
                        'action', 'model_name',
                        'performed_by_name', 'timestamp', 'object_repr'
                    )
                )

            return Response({
                'role':             user.role,
                'ministry_schema':  user.ministry_schema,
                'total_assets':     total_assets,
                'active_assets':    active_assets,
                'total_audit_records': total_audit,
                'total_warnings':   len(expired_list) + len(expiring_soon),
                'expired_assets':   expired_list,
                'expiring_soon':    expiring_soon,
                'expiring_later':   expiring_later,
                'recent_audit':     recent_audit,
            })

        except Exception as e:
            logger.error(f"Dashboard stats API error: {e}")
            return Response({
                'error':   True,
                'message': f'Error loading stats: {str(e)}',
                'code':    'server_error',
                'status':  500,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)