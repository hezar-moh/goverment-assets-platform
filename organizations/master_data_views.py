"""Web views for master data management (funding sources, location types, etc.)."""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import ProtectedError
from django_tenants.utils import schema_context

from authentication.decorators import login_required_custom, role_required


def _get_client_ip(request):
    """Extract real client IP — checks proxy headers first."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@login_required_custom
@role_required("MINISTRY_ADMIN")
def master_data_list_view(request):
    """Show all master data entries grouped by category, with optional ?category= filter."""
    user = request.user
    grouped_data = {}
    category_filter = request.GET.get("category", "")

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import MasterData

            qs = MasterData.objects.all().order_by("category", "sort_order", "label")
            if category_filter:
                qs = qs.filter(category=category_filter)

            # Group by category for display
            for item in qs:
                cat = item.get_category_display()
                if cat not in grouped_data:
                    grouped_data[cat] = {"category_code": item.category, "items": []}
                grouped_data[cat]["items"].append(item)

            total = MasterData.objects.count()

    except Exception as e:
        messages.error(request, f"Error loading master data: {str(e)}")
        total = 0

    from organizations.models import MasterData as MD

    categories = MD.CATEGORY_CHOICES

    return render(
        request,
        "organizations/master_data_list.html",
        {
            "grouped_data": grouped_data,
            "page_title": "Master Data Configuration",
            "categories": categories,
            "category_filter": category_filter,
            "total": total if "total" in locals() else 0,
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def master_data_create_view(request):
    """Add a new master data entry (funding source, location type, etc.)."""
    user = request.user
    from organizations.models import MasterData

    categories = MasterData.CATEGORY_CHOICES

    if request.method == "POST":
        category = request.POST.get("category", "")
        value = request.POST.get("value", "").strip().upper()
        label = request.POST.get("label", "").strip()
        sort_order = request.POST.get("sort_order", "0") or "0"

        errors = []
        if not category:
            errors.append("Category is required.")
        if not value:
            errors.append("Value code is required.")
        if not label:
            errors.append("Display label is required.")

        import re

        if value and not re.match(r"^[A-Z0-9_]+$", value):
            errors.append(
                "Value code must contain only uppercase letters, "
                "numbers, and underscores. Example: GOVT_BUDGET"
            )

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "organizations/master_data_form.html",
                {
                    "categories": categories,
                    "page_title": "Add Master Data",
                    "form_data": request.POST,
                },
            )

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import MasterData, AuditLog

                if MasterData.objects.filter(category=category, value=value).exists():
                    messages.error(
                        request, f"Value '{value}' already exists in this category."
                    )
                    return render(
                        request,
                        "organizations/master_data_form.html",
                        {
                            "categories": categories,
                            "page_title": "Add Master Data",
                            "form_data": request.POST,
                        },
                    )

                item = MasterData.objects.create(
                    category=category,
                    value=value,
                    label=label,
                    sort_order=int(sort_order),
                    is_active=True,
                )

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    performed_by_role=user.role,
                    action="CREATE",
                    model_name="MasterData",
                    object_id=str(item.id),
                    object_repr=str(item),
                    old_value=None,
                    new_value={
                        "category": category,
                        "value": value,
                        "label": label,
                    },
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

            messages.success(request, f"'{label}' added to {category} successfully.")
            return redirect("master_data_list")

        except Exception as e:
            messages.error(request, f"Error creating entry: {str(e)}")

    return render(
        request,
        "organizations/master_data_form.html",
        {
            "categories": categories,
            "page_title": "Add Master Data",
            "form_data": {},
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def master_data_edit_view(request, item_id):
    """Edit a master data entry (label, sort order, active status). Value code is fixed after creation."""
    user = request.user
    item = None

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import MasterData

            item = MasterData.objects.get(id=item_id)
    except Exception:
        messages.error(request, "Entry not found.")
        return redirect("master_data_list")

    from organizations.models import MasterData as MD

    categories = MD.CATEGORY_CHOICES

    if request.method == "POST":
        label = request.POST.get("label", "").strip()
        sort_order = request.POST.get("sort_order", "0") or "0"
        is_active = request.POST.get("is_active") == "on"

        if not label:
            messages.error(request, "Display label is required.")
            return render(
                request,
                "organizations/master_data_edit.html",
                {
                    "item": item,
                    "categories": categories,
                    "page_title": f"Edit: {item.label}",
                },
            )

        try:
            with schema_context(user.ministry_schema):
                from organizations.models import MasterData, AuditLog

                item = MasterData.objects.get(id=item_id)

                old_value = {
                    "label": item.label,
                    "sort_order": item.sort_order,
                    "is_active": item.is_active,
                }

                item.label = label
                item.sort_order = int(sort_order)
                item.is_active = is_active
                item.save()

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    performed_by_role=user.role,
                    action="UPDATE",
                    model_name="MasterData",
                    object_id=str(item.id),
                    object_repr=str(item),
                    old_value=old_value,
                    new_value={
                        "label": label,
                        "sort_order": int(sort_order),
                        "is_active": is_active,
                    },
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

            messages.success(request, f"'{label}' updated successfully.")
            return redirect("master_data_list")

        except Exception as e:
            messages.error(request, f"Error updating entry: {str(e)}")

    return render(
        request,
        "organizations/master_data_edit.html",
        {
            "item": item,
            "categories": categories,
            "page_title": f"Edit: {item.label}",
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def master_data_delete_view(request, item_id):
    """Delete a master data entry. POST only."""
    user = request.user

    if request.method != "POST":
        return redirect("master_data_list")

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import MasterData, AuditLog

            item = MasterData.objects.get(id=item_id)
            label = item.label

            AuditLog.objects.create(
                performed_by_id=user.id,
                performed_by_name=user.get_full_name() or user.username,
                performed_by_role=user.role,
                action="DELETE",
                model_name="MasterData",
                object_id=str(item.id),
                object_repr=str(item),
                old_value={
                    "category": item.category,
                    "value": item.value,
                    "label": item.label,
                },
                new_value=None,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )

            item.delete()

        messages.success(request, f"'{label}' deleted successfully.")

    except Exception:
        messages.error(request, "Entry not found.")

    return redirect("master_data_list")


@login_required_custom
@role_required("MINISTRY_ADMIN")
def master_data_seed_view(request):
    """Seed default master data for a ministry. Runs only once (get_or_create)."""
    user = request.user

    if request.method != "POST":
        return redirect("master_data_list")

    DEFAULT_DATA = [
        # Funding sources — where money came from
        ("FUNDING_SOURCE", "GOVT", "Government Budget", 1),
        ("FUNDING_SOURCE", "DONOR", "Donor / Grant", 2),
        ("FUNDING_SOURCE", "LOAN", "Government Loan", 3),
        ("FUNDING_SOURCE", "OWN", "Own Revenue", 4),
        ("FUNDING_SOURCE", "TRANSFER", "Asset Transfer", 5),
        ("FUNDING_SOURCE", "USAID", "USAID", 6),
        ("FUNDING_SOURCE", "WORLD_BANK", "World Bank", 7),
        # Acquisition methods — how asset was obtained
        ("ACQUISITION_METHOD", "PURCHASE", "Direct Purchase", 1),
        ("ACQUISITION_METHOD", "DONATION", "Donation / Gift", 2),
        ("ACQUISITION_METHOD", "TRANSFER", "Inter-dept Transfer", 3),
        ("ACQUISITION_METHOD", "FABRICATED", "Locally Fabricated", 4),
        ("ACQUISITION_METHOD", "LEASE", "Finance Lease", 5),
        # Location types — what kind of place
        ("LOCATION_TYPE", "OFFICE", "Office Building", 1),
        ("LOCATION_TYPE", "WAREHOUSE", "Warehouse / Store", 2),
        ("LOCATION_TYPE", "FIELD", "Field Site", 3),
        ("LOCATION_TYPE", "MEDICAL", "Medical Facility", 4),
        ("LOCATION_TYPE", "SCHOOL", "School / College", 5),
        ("LOCATION_TYPE", "LABORATORY", "Laboratory", 6),
        ("LOCATION_TYPE", "WORKSHOP", "Workshop / Garage", 7),
        # Disposal methods — how asset was removed
        ("DISPOSAL_METHOD", "AUCTION", "Public Auction", 1),
        ("DISPOSAL_METHOD", "WRITEOFF", "Write-off", 2),
        ("DISPOSAL_METHOD", "TRANSFER", "Transfer Out", 3),
        ("DISPOSAL_METHOD", "DESTROYED", "Destroyed", 4),
        ("DISPOSAL_METHOD", "DONATED", "Donated Out", 5),
        ("DISPOSAL_METHOD", "CONDEMNED", "Condemned", 6),
        # Cost centres — department responsible
        ("COST_CENTRE", "ADMIN", "Administration", 1),
        ("COST_CENTRE", "FINANCE", "Finance Department", 2),
        ("COST_CENTRE", "ICT", "ICT Department", 3),
        ("COST_CENTRE", "MEDICAL", "Medical Services", 4),
        ("COST_CENTRE", "ESTATES", "Estates and Works", 5),
        ("COST_CENTRE", "SECURITY", "Security Department", 6),
        ("COST_CENTRE", "HR", "Human Resources", 7),
    ]

    created = 0
    skipped = 0

    try:
        with schema_context(user.ministry_schema):
            from organizations.models import MasterData

            for category, value, label, sort_order in DEFAULT_DATA:
                obj, was_created = MasterData.objects.get_or_create(
                    category=category,
                    value=value,
                    defaults={
                        "label": label,
                        "sort_order": sort_order,
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        messages.success(
            request,
            f"Default data loaded: {created} entries created, "
            f"{skipped} already existed and were skipped.",
        )

    except Exception as e:
        messages.error(request, f"Error seeding data: {str(e)}")

    return redirect("master_data_list")


