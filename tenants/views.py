"""Web views for ministry onboarding, listing, detail, and toggle active."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_tenants.utils import schema_context

from authentication.decorators import login_required_custom, role_required
from .models import Ministry, Domain


@login_required_custom
@role_required('SUPER_ADMIN')
def ministry_list_view(request):
    """List all ministries with asset count, user count, and primary domain."""
    ministries = Ministry.objects.exclude(
        schema_name='public'
    ).prefetch_related('domains').order_by('name')

    from assets.models import Asset
    from authentication.models import CustomUser

    ministry_data = []
    for ministry in ministries:
        asset_count = 0
        try:
            with schema_context(ministry.schema_name):
                asset_count = Asset.objects.count()
        except Exception:
            pass

        user_count = CustomUser.objects.filter(
            ministry_schema=ministry.schema_name
        ).count()

        primary_domain = ministry.domains.filter(is_primary=True).first()

        ministry_data.append({
            'ministry':       ministry,
            'asset_count':    asset_count,
            'user_count':     user_count,
            'primary_domain': primary_domain,
        })

    return render(request, 'tenants/ministry_list.html', {
        'ministry_data': ministry_data,
        'page_title':    'Ministry Management',
        'total':         len(ministry_data),
    })


@login_required_custom
@role_required('SUPER_ADMIN')
def ministry_create_view(request):
    """Onboard a new ministry: create schema, domain mapping, and root OrgUnit."""
    if request.method == 'POST':
        name       = request.POST.get('name', '').strip()
        short_name = request.POST.get('short_name', '').strip().upper()
        schema_name = request.POST.get('schema_name', '').strip().lower()
        domain     = request.POST.get('domain', '').strip().lower()

        errors = []

        if not name:
            errors.append("Ministry name is required.")
        if not short_name:
            errors.append("Short name / abbreviation is required.")
        if not schema_name:
            errors.append("Schema name is required.")
        if not domain:
            errors.append("Domain is required.")

        import re
        if schema_name and not re.match(r'^[a-z][a-z0-9_]*$', schema_name):
            errors.append(
                "Schema name must start with a letter and contain only "
                "lowercase letters, numbers, and underscores. "
                "No spaces or hyphens. Example: mol_schema"
            )

        if schema_name and not schema_name.endswith('_schema'):
            errors.append(
                "Schema name must end with '_schema'. "
                f"Did you mean '{schema_name}_schema'?"
            )

        if Ministry.objects.filter(schema_name=schema_name).exists():
            errors.append(f"Schema name '{schema_name}' is already in use.")
        if Ministry.objects.filter(name=name).exists():
            errors.append(f"A ministry named '{name}' already exists.")
        if Domain.objects.filter(domain=domain).exists():
            errors.append(f"Domain '{domain}' is already registered.")

        existing = Ministry.objects.exclude(
            schema_name='public'
        ).values('name', 'schema_name').order_by('name')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'tenants/ministry_form.html', {
                'page_title': 'Onboard New Ministry',
                'form_data':  request.POST,
                'existing':   existing,
            })

        try:
            ministry = Ministry(
                schema_name=schema_name,
                name=name,
                short_name=short_name,
                is_active=True,
            )
            ministry.save()

            Domain.objects.create(
                domain=domain,
                tenant=ministry,
                is_primary=True,
            )

            from organizations.models import OrgUnit
            with schema_context(schema_name):
                OrgUnit.objects.create(
                    name=name,
                    code=short_name,
                    unit_type='MINISTRY',
                    parent=None,
                    is_active=True,
                )

            messages.success(
                request,
                f"Ministry '{name}' onboarded successfully. "
                f"Schema '{schema_name}' created and all tables migrated. "
                f"Domain '{domain}' registered."
            )
            return redirect('ministry_list')

        except Exception as e:
            messages.error(request, f"Error creating ministry: {str(e)}")
            try:
                Ministry.objects.filter(schema_name=schema_name).delete()
            except Exception:
                pass

    existing = Ministry.objects.exclude(
        schema_name='public'
    ).values('name', 'schema_name').order_by('name')

    return render(request, 'tenants/ministry_form.html', {
        'page_title': 'Onboard New Ministry',
        'form_data':  {},
        'existing':   existing,
    })


@login_required_custom
@role_required('SUPER_ADMIN')
def ministry_detail_view(request, ministry_id):
    """Show full details of one ministry: user list, asset count, org units, recent assets."""
    ministry = get_object_or_404(Ministry, id=ministry_id)

    if ministry.schema_name == 'public':
        messages.error(request, "Cannot view the public schema as a ministry.")
        return redirect('ministry_list')

    from authentication.models import CustomUser
    from assets.models import Asset
    from organizations.models import OrgUnit

    users = CustomUser.objects.filter(
        ministry_schema=ministry.schema_name
    ).order_by('role', 'username')

    asset_count  = 0
    org_units    = []
    recent_assets = []

    try:
        with schema_context(ministry.schema_name):
            asset_count   = Asset.objects.count()
            org_units     = list(OrgUnit.objects.all().order_by('unit_type', 'name'))
            recent_assets = list(
                Asset.objects.select_related('category')
                .order_by('-created_at')[:5]
            )
    except Exception:
        pass

    primary_domain = ministry.domains.filter(is_primary=True).first()

    return render(request, 'tenants/ministry_detail.html', {
        'ministry':       ministry,
        'users':          users,
        'asset_count':    asset_count,
        'org_units':      org_units,
        'recent_assets':  recent_assets,
        'primary_domain': primary_domain,
        'page_title':     ministry.name,
    })


@login_required_custom
@role_required('SUPER_ADMIN')
def ministry_toggle_active_view(request, ministry_id):
    """Activate or deactivate a ministry. Schema and data are preserved."""
    if request.method != 'POST':
        return redirect('ministry_list')

    ministry = get_object_or_404(Ministry, id=ministry_id)

    if ministry.schema_name == 'public':
        messages.error(request, "Cannot deactivate the public schema.")
        return redirect('ministry_list')

    ministry.is_active = not ministry.is_active
    ministry.save()

    action = "activated" if ministry.is_active else "deactivated"
    messages.success(request, f"Ministry '{ministry.name}' {action} successfully.")
    return redirect('ministry_list')