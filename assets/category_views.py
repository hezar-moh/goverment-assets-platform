from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import ProtectedError
from django_tenants.utils import schema_context

from authentication.decorators import login_required_custom, role_required


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


@login_required_custom
@role_required("MINISTRY_ADMIN")
def asset_category_list_view(request):
    user = request.user
    categories = []

    try:
        with schema_context(user.ministry_schema):
            from assets.models import AssetCategory

            categories = list(AssetCategory.objects.all().order_by("name"))
    except Exception as e:
        messages.error(request, f"Error loading categories: {str(e)}")

    return render(
        request,
        "assets/asset_category_list.html",
        {
            "categories": categories,
            "page_title": "Asset Categories",
            "total": len(categories),
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def asset_category_create_view(request):
    user = request.user

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        code = request.POST.get("code", "").strip().upper()
        description = request.POST.get("description", "").strip()

        errors = []
        if not name:
            errors.append("Category name is required.")
        if not code:
            errors.append("Category code is required.")

        import re

        if code and not re.match(r"^[A-Z0-9]+$", code):
            errors.append(
                "Code must contain only uppercase letters and numbers. "
                "No spaces or symbols. Example: ICT, VEH, FURN"
            )

        existing_categories = []
        try:
            with schema_context(user.ministry_schema):
                from assets.models import AssetCategory

                existing_categories = list(
                    AssetCategory.objects.filter(is_active=True).order_by("code")
                )
        except Exception:
            pass

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "assets/asset_category_form.html",
                {
                    "page_title": "Add Asset Category",
                    "form_data": request.POST,
                    "existing_categories": existing_categories,
                },
            )

        try:
            with schema_context(user.ministry_schema):
                from assets.models import AssetCategory
                from organizations.models import AuditLog

                if AssetCategory.objects.filter(code=code).exists():
                    messages.error(
                        request, f"Code '{code}' is already used by another category."
                    )
                    return render(
                        request,
                        "assets/asset_category_form.html",
                        {
                            "page_title": "Add Asset Category",
                            "form_data": request.POST,
                        },
                    )

                category = AssetCategory.objects.create(
                    name=name,
                    code=code,
                    description=description,
                    is_active=True,
                )

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    performed_by_role=user.role,
                    action="CREATE",
                    model_name="AssetCategory",
                    object_id=str(category.id),
                    object_repr=str(category),
                    old_value=None,
                    new_value={"name": name, "code": code},
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

            messages.success(
                request,
                f"Category '{name}' ({code}) created successfully. "
                f"It will now appear in the asset registration form.",
            )
            return redirect("asset_category_list")

        except Exception as e:
            messages.error(request, f"Error creating category: {str(e)}")

    existing_categories = []
    try:
        with schema_context(user.ministry_schema):
            from assets.models import AssetCategory

            existing_categories = list(
                AssetCategory.objects.filter(is_active=True).order_by("code")
            )
    except Exception:
        pass

    return render(
        request,
        "assets/asset_category_form.html",
        {
            "page_title": "Add Asset Category",
            "form_data": {},
            "existing_categories": existing_categories,
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def asset_category_edit_view(request, category_id):
    user = request.user
    category = None

    try:
        with schema_context(user.ministry_schema):
            from assets.models import AssetCategory

            category = AssetCategory.objects.get(id=category_id)
    except Exception:
        messages.error(request, "Category not found.")
        return redirect("asset_category_list")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Category name is required.")
            return render(
                request,
                "assets/asset_category_edit.html",
                {
                    "category": category,
                    "page_title": f"Edit: {category.name}",
                },
            )

        try:
            with schema_context(user.ministry_schema):
                from assets.models import AssetCategory
                from organizations.models import AuditLog

                category = AssetCategory.objects.get(id=category_id)
                old_name = category.name
                old_active = category.is_active

                category.name = name
                category.description = description
                category.is_active = is_active
                category.save()

                AuditLog.objects.create(
                    performed_by_id=user.id,
                    performed_by_name=user.get_full_name() or user.username,
                    performed_by_role=user.role,
                    action="UPDATE",
                    model_name="AssetCategory",
                    object_id=str(category.id),
                    object_repr=str(category),
                    old_value={"name": old_name, "is_active": old_active},
                    new_value={"name": name, "is_active": is_active},
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                )

            messages.success(request, f"Category '{name}' updated successfully.")
            return redirect("asset_category_list")

        except Exception as e:
            messages.error(request, f"Error updating category: {str(e)}")

    return render(
        request,
        "assets/asset_category_edit.html",
        {
            "category": category,
            "page_title": f"Edit: {category.name}",
        },
    )


@login_required_custom
@role_required("MINISTRY_ADMIN")
def asset_category_delete_view(request, category_id):
    user = request.user

    if request.method != "POST":
        return redirect("asset_category_list")

    try:
        with schema_context(user.ministry_schema):
            from assets.models import AssetCategory
            from organizations.models import AuditLog

            category = AssetCategory.objects.get(id=category_id)

            AuditLog.objects.create(
                performed_by_id=user.id,
                performed_by_name=user.get_full_name() or user.username,
                performed_by_role=user.role,
                action="DELETE",
                model_name="AssetCategory",
                object_id=str(category.id),
                object_repr=str(category),
                old_value={
                    "name": category.name,
                    "code": category.code,
                    "is_active": category.is_active,
                },
                new_value=None,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )

            category.delete()

        messages.success(request, f"Category '{category.name}' deleted successfully.")

    except ProtectedError:
        messages.error(
            request,
            "Cannot delete one or more assets are assigned to this category. "
            "Mark it as Inactive instead.",
        )
    except Exception:
        messages.error(request, "Category not found.")

    return redirect("asset_category_list")
