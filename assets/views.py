# Purpose: Web views for the asset register — list, create, edit, delete assets through the browser.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_tenants.utils import schema_context

from authentication.decorators import (
    login_required_custom, role_required, ministry_isolation_check,
)
from .models import Asset, AssetCategory



def _load_asset_form_data(ministry_schema):
    """Load dropdown options for the asset form — categories, org units, master data lists."""
    result = {
        'categories':          [],
        'org_units':           [],
        'funding_sources':     [],
        'acquisition_methods': [],
        'location_types':      [],
        'disposal_methods':    [],
        'cost_centres':        [],
    }

    try:
        with schema_context(ministry_schema):
            from assets.models import AssetCategory
            from organizations.models import OrgUnit, MasterData

            result['categories'] = list(
                AssetCategory.objects.filter(
                    is_active=True
                ).order_by('name')
            )
            result['org_units'] = list(
                OrgUnit.objects.filter(
                    unit_type='FACILITY',
                    is_active=True
                ).order_by('name')
            )
            result['funding_sources'] = list(
                MasterData.objects.filter(
                    category='FUNDING_SOURCE',
                    is_active=True
                ).order_by('sort_order', 'label')
            )
            result['acquisition_methods'] = list(
                MasterData.objects.filter(
                    category='ACQUISITION_METHOD',
                    is_active=True
                ).order_by('sort_order', 'label')
            )
            result['location_types'] = list(
                MasterData.objects.filter(
                    category='LOCATION_TYPE',
                    is_active=True
                ).order_by('sort_order', 'label')
            )
            result['disposal_methods'] = list(
                MasterData.objects.filter(
                    category='DISPOSAL_METHOD',
                    is_active=True
                ).order_by('sort_order', 'label')
            )
            result['cost_centres'] = list(
                MasterData.objects.filter(
                    category='COST_CENTRE',
                    is_active=True
                ).order_by('sort_order', 'label')
            )
    except Exception:
        pass

    return result



def generate_asset_number(ministry_schema, category_code):
    """Generate a unique asset number like MOH-ICT-2025-0001.
    Finds the highest existing sequence and increments from there
    to avoid race conditions under concurrent requests.
    """
    from django.utils import timezone

    year   = timezone.now().year
    prefix = ministry_schema.replace('_schema', '').upper()[:3]
    base   = f"{prefix}-{category_code}-{year}-"

    # Find the highest existing sequence number
    existing = Asset.objects.filter(
        asset_number__startswith=base
    ).order_by('-asset_number').first()

    if existing:
        try:
            last_seq = int(existing.asset_number.split('-')[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0

    # Increment until we find a unique number
    # Handles concurrent creation gracefully
    sequence = last_seq + 1
    while True:
        asset_number = f"{base}{str(sequence).zfill(4)}"
        if not Asset.objects.filter(
            asset_number=asset_number
        ).exists():
            return asset_number
        sequence += 1

@login_required_custom
@ministry_isolation_check
def asset_list_view(request):
    """Show all assets for the logged-in user's ministry, with filtering and pagination."""
    user = request.user

    if user.role == "SUPER_ADMIN":
        # Super Admin operates at platform level, not inside one ministry schema
        return render(
            request,
            "assets/asset_list.html",
            {
                "assets": [],
                "is_super_admin": True,
                "page_title": "Asset Register",
            },
        )

    assets = []
    categories = []

    try:
        with schema_context(user.ministry_schema):
            qs = Asset.objects.select_related('category').all()

            status_filter = request.GET.get('status', '')
            if status_filter:
                qs = qs.filter(status=status_filter)

            category_filter = request.GET.get('category', '')
            if category_filter:
                qs = qs.filter(category_id=category_filter)

            search = request.GET.get('search', '').strip()
            if search:
                qs = qs.filter(
                    name__icontains=search
                ) | qs.filter(
                    asset_number__icontains=search
                )

            # Paginate — 20 assets per page
            from authentication.pagination import paginate_queryset
            page, paginator = paginate_queryset(qs, request, per_page=20)
            assets = list(page.object_list)
            categories = list(AssetCategory.objects.filter(is_active=True))

    except Exception as e:
        messages.error(request, f"Error loading assets: {str(e)}")

    return render(request, 'assets/asset_list.html', {
        'assets':          assets,
        'categories':      categories,
        'is_super_admin':  False,
        'page_title':      'Asset Register',
        'status_filter':   status_filter if 'status_filter' in locals() else '',
        'category_filter': category_filter if 'category_filter' in locals() else '',
        'search':          search if 'search' in locals() else '',
        'can_edit':        user.role in ['MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK'],
        'STATUS_CHOICES':  Asset.STATUS_CHOICES,
        'page':            page if 'page' in locals() else None,
        'paginator':       paginator if 'paginator' in locals() else None,
    })


@login_required_custom
@role_required('MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK')
def asset_create_view(request):
    """Show the create form on GET. Validate and save on POST, then redirect to the detail page."""
    user = request.user
    form_data = _load_asset_form_data(user.ministry_schema)

    if request.method == 'POST':
        asset_number       = request.POST.get('asset_number', '').strip()
        name               = request.POST.get('name', '').strip()
        category_id        = request.POST.get('category', '')
        serial_number      = request.POST.get('serial_number', '').strip()
        manufacturer       = request.POST.get('manufacturer', '').strip()
        model_number       = request.POST.get('model_number', '').strip()
        supplier_name      = request.POST.get('supplier_name', '').strip()
        po_number          = request.POST.get('purchase_order_number', '').strip()
        status             = request.POST.get('status', 'ACTIVE')
        condition          = request.POST.get('condition', 'GOOD')
        location_desc      = request.POST.get('location_description', '').strip()
        location_type      = request.POST.get('location_type', '').strip()
        org_unit_id        = request.POST.get('org_unit_id', '') or None
        useful_life        = request.POST.get('useful_life_years', '') or None
        acquisition_date   = request.POST.get('acquisition_date') or None
        warranty_expiry    = request.POST.get('warranty_expiry_date') or None
        asset_expiry       = request.POST.get('asset_expiry_date') or None
        acquisition_cost   = request.POST.get('acquisition_cost') or None
        current_value      = request.POST.get('current_value') or None
        funding_source     = request.POST.get('funding_source', '').strip()
        acquisition_method = request.POST.get('acquisition_method', '').strip()
        cost_centre        = request.POST.get('cost_centre', '').strip()
        description        = request.POST.get('description', '').strip()

        errors = []
        if not name:
            errors.append("Asset name is required.")
        if not category_id:
            errors.append("Category is required.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'assets/asset_form.html', {
                'asset': None,
                'page_title': 'Register New Asset',
                'STATUS_CHOICES': Asset.STATUS_CHOICES,
                'CONDITION_CHOICES': Asset.CONDITION_CHOICES,
                'form_data': request.POST,
                **form_data,
            })

        try:
            with schema_context(user.ministry_schema):
                category = AssetCategory.objects.get(id=category_id)

                if not asset_number:
                    asset_number = generate_asset_number(
                        user.ministry_schema, category.code
                    )

                if Asset.objects.filter(asset_number=asset_number).exists():
                    messages.error(
                        request,
                        f"Asset number '{asset_number}' already exists."
                    )
                    return render(request, 'assets/asset_form.html', {
                        'asset': None,
                        'page_title': 'Register New Asset',
                        'STATUS_CHOICES': Asset.STATUS_CHOICES,
                        'CONDITION_CHOICES': Asset.CONDITION_CHOICES,
                        'form_data': request.POST,
                        **form_data,
                    })

                org_unit_name = ''
                if org_unit_id:
                    from organizations.models import OrgUnit
                    try:
                        org_unit_obj  = OrgUnit.objects.get(id=org_unit_id)
                        org_unit_name = org_unit_obj.name
                    except OrgUnit.DoesNotExist:
                        org_unit_id = None

                asset = Asset.objects.create(
                    asset_number=asset_number,
                    name=name,
                    category=category,
                    serial_number=serial_number or None,
                    manufacturer=manufacturer,
                    model_number=model_number,
                    supplier_name=supplier_name,
                    purchase_order_number=po_number,
                    status=status,
                    condition=condition,
                    location_description=location_desc,
                    location_type=location_type,
                    org_unit_id=org_unit_id,
                    org_unit_name=org_unit_name,
                    useful_life_years=useful_life,
                    acquisition_date=acquisition_date,
                    warranty_expiry_date=warranty_expiry,
                    asset_expiry_date=asset_expiry,
                    acquisition_cost=acquisition_cost,
                    current_value=current_value,
                    funding_source=funding_source,
                    acquisition_method=acquisition_method,
                    cost_centre=cost_centre,
                    description=description,
                    registered_by_id=user.id,
                    registered_by_name=user.get_full_name() or user.username,
                )

                _log_asset_action(
                    schema_name=user.ministry_schema,
                    user=user,
                    action='CREATE',
                    asset=asset,
                    old_value=None,
                )

            messages.success(
                request,
                f"Asset '{name}' registered with number {asset_number}."
            )
            return redirect('asset_detail', asset_id=asset.id)

        except Exception as e:
            messages.error(request, f"Error creating asset: {str(e)}")

    return render(request, 'assets/asset_form.html', {
        'asset': None,
        'page_title': 'Register New Asset',
        'STATUS_CHOICES': Asset.STATUS_CHOICES,
        'CONDITION_CHOICES': Asset.CONDITION_CHOICES,
        'form_data': {},
        **form_data,
    })

@login_required_custom
@ministry_isolation_check
def asset_detail_view(request, asset_id):
    """Show full details of a single asset."""
    user = request.user

    if user.role == "SUPER_ADMIN":
        messages.info(
            request, "Super Admin must select a ministry to view asset details."
        )
        return redirect("asset_list")

    asset = None
    try:
        with schema_context(user.ministry_schema):
            # Fetch category in the same query so it works inside the schema context
            asset = Asset.objects.select_related("category").get(id=asset_id)
            if asset is None:
                return redirect("asset_list")
    except Asset.DoesNotExist:
        messages.error(request, "Asset not found.")
        return redirect("asset_list")
    except Exception as e:
        messages.error(request, f"Error loading asset: {str(e)}")
        return redirect("asset_list")

    return render(
        request,
        "assets/asset_detail.html",
        {
            "asset": asset,
            "page_title": f"Asset: {asset.asset_number}",
            "can_edit": user.role
            in ["MINISTRY_ADMIN", "AGENCY_MANAGER", "FACILITY_CLERK"],
        },
    )


@login_required_custom
@role_required('MINISTRY_ADMIN', 'AGENCY_MANAGER', 'FACILITY_CLERK')
def asset_edit_view(request, asset_id):
    """Edit an existing asset. Captures old values before changes for the audit trail."""
    user = request.user

    # Load all dropdown data first using the helper function
    form_data = _load_asset_form_data(user.ministry_schema)

    # Load the asset itself separately
    asset = None
    try:
        with schema_context(user.ministry_schema):
            asset = Asset.objects.select_related('category').get(id=asset_id)
    except Asset.DoesNotExist:
        messages.error(request, "Asset not found.")
        return redirect('asset_list')
    except Exception as e:
        messages.error(request, f"Error loading asset: {str(e)}")
        return redirect('asset_list')

    if request.method == 'POST':
        try:
            with schema_context(user.ministry_schema):
                asset = Asset.objects.select_related('category').get(id=asset_id)

                old_value = {
                    'name':               asset.name,
                    'status':             asset.status,
                    'condition':          asset.condition,
                    'manufacturer':       asset.manufacturer,
                    'location_description': asset.location_description,
                    'acquisition_cost':   str(asset.acquisition_cost or ''),
                    'current_value':      str(asset.current_value or ''),
                    'asset_expiry_date':  str(asset.asset_expiry_date or ''),
                }

                asset.name               = request.POST.get('name', asset.name).strip()
                asset.status             = request.POST.get('status', asset.status)
                asset.condition          = request.POST.get('condition', asset.condition)
                asset.manufacturer       = request.POST.get('manufacturer', asset.manufacturer).strip()
                asset.model_number       = request.POST.get('model_number', asset.model_number).strip()
                asset.supplier_name      = request.POST.get('supplier_name', asset.supplier_name).strip()
                asset.purchase_order_number = request.POST.get('purchase_order_number', asset.purchase_order_number).strip()
                asset.location_description  = request.POST.get('location_description', asset.location_description).strip()
                asset.funding_source     = request.POST.get('funding_source', asset.funding_source).strip()
                asset.acquisition_method = request.POST.get('acquisition_method', asset.acquisition_method).strip()
                asset.cost_centre        = request.POST.get('cost_centre', asset.cost_centre).strip()
                asset.location_type      = request.POST.get('location_type', asset.location_type).strip()
                asset.description        = request.POST.get('description', asset.description).strip()

                # Disposal fields — only saved when status is DISPOSED
                if request.POST.get('status') == 'DISPOSED':
                    asset.disposal_method = request.POST.get('disposal_method', '').strip()
                    asset.disposal_date   = request.POST.get('disposal_date') or None
                    asset.disposal_notes  = request.POST.get('disposal_notes', '').strip()
                asset.useful_life_years  = request.POST.get('useful_life_years') or None

                asset.acquisition_date      = request.POST.get('acquisition_date') or None
                asset.warranty_expiry_date  = request.POST.get('warranty_expiry_date') or None
                asset.asset_expiry_date     = request.POST.get('asset_expiry_date') or None

                cost = request.POST.get('acquisition_cost')
                if cost:
                    asset.acquisition_cost = cost

                value = request.POST.get('current_value')
                if value:
                    asset.current_value = value

                category_id = request.POST.get('category')
                if category_id:
                    asset.category = AssetCategory.objects.get(id=category_id)

                org_unit_id = request.POST.get('org_unit_id') or None
                if org_unit_id:
                    from organizations.models import OrgUnit
                    try:
                        org_unit_obj       = OrgUnit.objects.get(id=org_unit_id)
                        asset.org_unit_id  = org_unit_obj.id
                        asset.org_unit_name = org_unit_obj.name
                    except OrgUnit.DoesNotExist:
                        pass

                asset.save()

                _log_asset_action(
                    schema_name=user.ministry_schema,
                    user=user,
                    action='UPDATE',
                    asset=asset,
                    old_value=old_value,
                )

            messages.success(request, f"Asset '{asset.name}' updated successfully.")
            return redirect('asset_detail', asset_id=asset.id)

        except Exception as e:
            messages.error(request, f"Error updating asset: {str(e)}")

    return render(request, 'assets/asset_form.html', {
        'asset': asset,
        'page_title': f'Edit: {asset.asset_number}',
        'STATUS_CHOICES': Asset.STATUS_CHOICES,
        'CONDITION_CHOICES': Asset.CONDITION_CHOICES,
        'is_edit': True,
        **form_data,
    })

@login_required_custom
@role_required("MINISTRY_ADMIN")
def asset_delete_view(request, asset_id):
    """Delete an asset (POST only). Only Ministry Admin can do this."""
    user = request.user

    if request.method == "POST":
        try:
            with schema_context(user.ministry_schema):
                asset = get_object_or_404(Asset, id=asset_id)
                asset_name = asset.name
                asset_number = asset.asset_number

                # Log before deleting so we have a record
                _log_asset_action(
                    schema_name=user.ministry_schema,
                    user=user,
                    action="DELETE",
                    asset=asset,
                    old_value={
                        "asset_number": asset_number,
                        "name": asset_name,
                        "status": asset.status,
                    },
                )

                asset.delete()

            messages.success(request, f"Asset '{asset_name}' ({asset_number}) deleted.")
            return redirect("asset_list")

        except Exception as e:
            messages.error(request, f"Error deleting asset: {str(e)}")
            return redirect("asset_list")

    return redirect("asset_list")


def _log_asset_action(schema_name, user, action, asset, old_value):
    """Write an audit log entry for asset create/update/delete. Shared by all views so the logic stays in one place."""
    try:
        from organizations.models import AuditLog

        new_value = None
        if action != "DELETE":
            new_value = {
                "asset_number": asset.asset_number,
                "name": asset.name,
                "status": asset.status,
                "condition": asset.condition,
            }

        with schema_context(schema_name):
            AuditLog.objects.create(
                performed_by_id=user.id,
                performed_by_name=user.get_full_name() or user.username,
                action=action,
                model_name="Asset",
                object_id=str(asset.id),
                object_repr=str(asset),
                old_value=old_value,
                new_value=new_value,
            )
    except Exception:
        # Never block the main action because audit logging failed
        pass
