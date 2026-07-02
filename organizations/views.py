"""Web views for organisational hierarchy and audit logs."""
from django.shortcuts import render, redirect
from django.contrib import messages
from django_tenants.utils import schema_context

from authentication.decorators import (
    login_required_custom,
    role_required,
    ministry_isolation_check
)


@login_required_custom
@role_required('SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER')
def org_unit_list_view(request):
    """Show the full org hierarchy as a tree (Ministry → Agency → Facility). Super Admin sees a placeholder."""
    user = request.user

    if user.role == 'SUPER_ADMIN':
        return render(request, 'organizations/org_unit_list.html', {
            'is_super_admin': True,
            'page_title': 'Organisation Hierarchy',
            'ministries': [],
            'tree': [],
        })

    tree = []
    try:
        with schema_context(user.ministry_schema):
            from organizations.models import OrgUnit

            all_units = list(
                OrgUnit.objects.all().order_by('unit_type', 'name')
            )

            ministries = [u for u in all_units if u.unit_type == 'MINISTRY']

            for ministry in ministries:
                agencies = [
                    u for u in all_units
                    if u.unit_type == 'AGENCY' and u.parent_id == ministry.id
                ]
                agency_nodes = []
                for agency in agencies:
                    facilities = [
                        u for u in all_units
                        if u.unit_type == 'FACILITY' and u.parent_id == agency.id
                    ]
                    agency_nodes.append({
                        'unit': agency,
                        'facilities': facilities,
                    })

                tree.append({
                    'unit': ministry,
                    'agencies': agency_nodes,
                })

    except Exception as e:
        messages.error(request, f"Error loading organisation: {str(e)}")

    return render(request, 'organizations/org_unit_list.html', {
        'is_super_admin': False,
        'tree': tree,
        'page_title': 'Organisation Hierarchy',
        'can_manage': user.role == 'MINISTRY_ADMIN',
        'ministry_schema': user.ministry_schema,
    })


@login_required_custom
@role_required('MINISTRY_ADMIN')
def org_unit_create_view(request):
    """Create an Agency or Facility unit under the user's ministry."""
    user = request.user
    parent_units = []
    unit_type_choices = []

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import OrgUnit

            ministry_units = list(
                OrgUnit.objects.filter(unit_type='MINISTRY', is_active=True)
            )
            agency_units = list(
                OrgUnit.objects.filter(unit_type='AGENCY', is_active=True)
            )
            parent_units = ministry_units + agency_units

    except Exception as e:
        messages.error(request, f"Error loading data: {str(e)}")

    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        code      = request.POST.get('code', '').strip().upper()
        unit_type = request.POST.get('unit_type', '')
        parent_id = request.POST.get('parent_id', '') or None

        errors = []
        if not name:
            errors.append("Unit name is required.")
        if not unit_type:
            errors.append("Unit type is required.")
        if unit_type not in ['AGENCY', 'FACILITY']:
            errors.append("You can only create Agency or Facility units.")
        if unit_type == 'AGENCY' and not parent_id:
            errors.append("An Agency must have a Ministry as its parent.")
        if unit_type == 'FACILITY' and not parent_id:
            errors.append("A Facility must have an Agency as its parent.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'organizations/org_unit_form.html', {
                'parent_units': parent_units,
                'page_title':   'Add Organisation Unit',
                'form_data':    request.POST,
            })

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import OrgUnit, AuditLog

                if parent_id:
                    parent = OrgUnit.objects.get(id=parent_id)

                    if unit_type == 'AGENCY' and parent.unit_type != 'MINISTRY':
                        messages.error(
                            request,
                            "An Agency must be placed directly under a Ministry."
                        )
                        return redirect('org_unit_create')

                    if unit_type == 'FACILITY' and parent.unit_type != 'AGENCY':
                        messages.error(
                            request,
                            "A Facility must be placed directly under an Agency."
                        )
                        return redirect('org_unit_create')
                else:
                    parent = None

                org_unit = OrgUnit.objects.create(
                    name=name,
                    code=code,
                    unit_type=unit_type,
                    parent=parent,
                    is_active=True,
                )

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    action='CREATE',
                    model_name='OrgUnit',
                    object_id=str(org_unit.id),
                    object_repr=str(org_unit),
                    old_value=None,
                    new_value={
                        'name': name,
                        'unit_type': unit_type,
                        'parent': str(parent) if parent else None,
                    },
                )

            messages.success(
                request,
                f"{unit_type.title()} '{name}' created successfully."
            )
            return redirect('org_unit_list')

        except Exception as e:
            messages.error(request, f"Error creating unit: {str(e)}")

    return render(request, 'organizations/org_unit_form.html', {
        'parent_units': parent_units,
        'page_title':   'Add Organisation Unit',
        'form_data':    {},
    })


@login_required_custom
@role_required('MINISTRY_ADMIN')
def org_unit_edit_view(request, unit_id):
    """Edit an existing OrgUnit (name, code, active status). Cannot change type or MINISTRY parent."""
    user = request.user
    org_unit = None
    parent_units = []

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import OrgUnit
            org_unit = OrgUnit.objects.select_related('parent').get(id=unit_id)
            parent_units = list(
                OrgUnit.objects.exclude(id=unit_id)
                .filter(is_active=True)
                .order_by('unit_type', 'name')
            )
    except OrgUnit.DoesNotExist:
        messages.error(request, "Organisation unit not found.")
        return redirect('org_unit_list')
    except Exception as e:
        messages.error(request, f"Error loading unit: {str(e)}")
        return redirect('org_unit_list')

    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        code      = request.POST.get('code', '').strip().upper()
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, "Unit name is required.")
            return render(request, 'organizations/org_unit_edit.html', {
                'org_unit':     org_unit,
                'parent_units': parent_units,
                'page_title':   f'Edit: {org_unit.name}',
            })

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import OrgUnit, AuditLog
                org_unit = OrgUnit.objects.select_related('parent').get(id=unit_id)

                old_value = {
                    'name':      org_unit.name,
                    'code':      org_unit.code,
                    'is_active': org_unit.is_active,
                }

                org_unit.name      = name
                org_unit.code      = code
                org_unit.is_active = is_active
                org_unit.save()

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    action='UPDATE',
                    model_name='OrgUnit',
                    object_id=str(org_unit.id),
                    object_repr=str(org_unit),
                    old_value=old_value,
                    new_value={
                        'name':      name,
                        'code':      code,
                        'is_active': is_active,
                    },
                )

            messages.success(request, f"'{name}' updated successfully.")
            return redirect('org_unit_list')

        except Exception as e:
            messages.error(request, f"Error updating unit: {str(e)}")

    return render(request, 'organizations/org_unit_edit.html', {
        'org_unit':     org_unit,
        'parent_units': parent_units,
        'page_title':   f'Edit: {org_unit.name}',
    })


@login_required_custom
@role_required('MINISTRY_ADMIN')
def org_unit_delete_view(request, unit_id):
    """Delete an OrgUnit. Cannot delete units with children or the root MINISTRY unit."""
    user = request.user

    if request.method != 'POST':
        return redirect('org_unit_list')

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import OrgUnit, AuditLog
            org_unit = OrgUnit.objects.get(id=unit_id)

            if org_unit.unit_type == 'MINISTRY':
                messages.error(
                    request,
                    "Cannot delete the root Ministry unit. "
                    "It was created during onboarding."
                )
                return redirect('org_unit_list')

            children_count = OrgUnit.objects.filter(parent=org_unit).count()
            if children_count > 0:
                messages.error(
                    request,
                    f"Cannot delete '{org_unit.name}' — it has "
                    f"{children_count} child unit(s). "
                    f"Remove or reassign them first."
                )
                return redirect('org_unit_list')

            unit_name = org_unit.name

            AuditLog.objects.create(
                performed_by_id=user.id,
                performed_by_name=user.get_full_name() or user.username,
                action='DELETE',
                model_name='OrgUnit',
                object_id=str(org_unit.id),
                object_repr=str(org_unit),
                old_value={
                    'name':      org_unit.name,
                    'unit_type': org_unit.unit_type,
                },
                new_value=None,
            )

            org_unit.delete()

        messages.success(request, f"'{unit_name}' deleted successfully.")

    except OrgUnit.DoesNotExist:
        messages.error(request, "Unit not found.")
    except Exception as e:
        messages.error(request, f"Error deleting unit: {str(e)}")

    return redirect('org_unit_list')

@login_required_custom
@role_required('SUPER_ADMIN', 'MINISTRY_ADMIN', 'AUDITOR')
def audit_log_view(request):
    """Show paginated audit trail for the user's ministry."""
    user = request.user
    logs = []
    action_filter = request.GET.get('action', '')

    if user.role == 'SUPER_ADMIN':
        return render(request, 'organizations/audit_log.html', {
            'logs': [],
            'is_super_admin': True,
            'page_title': 'Audit Logs',
            'action_filter': '',
        })

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import AuditLog
            qs = AuditLog.objects.all()
            if action_filter:
                qs = qs.filter(action=action_filter)

            from authentication.pagination import paginate_queryset
            page, paginator = paginate_queryset(qs, request, per_page=25)
            logs = list(page.object_list)
    except Exception as e:
        messages.error(request, f"Error loading audit logs: {str(e)}")

    return render(request, 'organizations/audit_log.html', {
        'logs':          logs,
        'is_super_admin': False,
        'page_title':    'Audit Logs',
        'action_filter': action_filter,
        'page':          page if 'page' in locals() else None,
        'paginator':     paginator if 'paginator' in locals() else None,
    })