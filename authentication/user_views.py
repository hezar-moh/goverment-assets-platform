# Purpose: Web views for user management — list, create, edit, toggle active, and reset passwords.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import CustomUser
from .decorators import login_required_custom, role_required
import logging
logger = logging.getLogger('authentication')


@login_required_custom
@role_required("SUPER_ADMIN", "MINISTRY_ADMIN", "AGENCY_MANAGER")
def user_list_view(request):
    """Show users the current user can see. Super Admin sees everyone; others see only their ministry."""
    user = request.user

    if user.role == 'SUPER_ADMIN':
        qs = CustomUser.objects.all().order_by('role', 'username')
        can_create = True
    else:
        qs = CustomUser.objects.filter(
            ministry_schema=user.ministry_schema
        ).order_by('role', 'username')
        can_create = user.role in ['MINISTRY_ADMIN', 'AGENCY_MANAGER']

    from authentication.pagination import paginate_queryset
    page, paginator = paginate_queryset(qs, request, per_page=20)

    return render(request, 'authentication/user_list.html', {
        'users':        list(page.object_list),
        'page_title':   'User Management',
        'can_create':   can_create,
        'editor_role':  user.role,
        'editor_id':    user.id,
        'editor_schema': user.ministry_schema,
        'page':         page,
        'paginator':    paginator,
    })


@login_required_custom
@role_required('SUPER_ADMIN', 'MINISTRY_ADMIN', 'AGENCY_MANAGER')
def user_create_view(request):
    """Create a user in Keycloak first, then Django. Roll back Keycloak if Django fails — both must stay in sync."""
    creator = request.user

    CREATABLE_ROLES = {
        'SUPER_ADMIN':    ['MINISTRY_ADMIN'],
        'MINISTRY_ADMIN': ['AGENCY_MANAGER', 'AUDITOR', 'FACILITY_CLERK'],
        'AGENCY_MANAGER': ['FACILITY_CLERK'],
    }
    allowed_roles = CREATABLE_ROLES.get(creator.role, [])

    from tenants.models import Ministry
    ministries = Ministry.objects.exclude(schema_name='public')

    if request.method == 'POST':
        username         = request.POST.get('username', '').strip()
        first_name       = request.POST.get('first_name', '').strip()
        last_name        = request.POST.get('last_name', '').strip()
        email            = request.POST.get('email', '').strip()
        role             = request.POST.get('role', '')
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        ministry_schema  = request.POST.get('ministry_schema', '')

        if creator.role in ('MINISTRY_ADMIN', 'AGENCY_MANAGER'):
            ministry_schema = creator.ministry_schema

        errors = []
        if not username:
            errors.append("Username is required.")
        if not first_name or not last_name:
            errors.append("Full name is required.")
        if not role:
            errors.append("Role is required.")
        if role not in allowed_roles:
            errors.append(f"You are not allowed to create a {role} user.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if CustomUser.objects.filter(username=username).exists():
            errors.append(f"Username '{username}' is already taken.")
        if role != 'SUPER_ADMIN' and not ministry_schema:
            errors.append("Ministry schema is required for this role.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'authentication/user_form.html', {
                'allowed_roles': allowed_roles,
                'ministries':    ministries,
                'page_title':    'Create New User',
                'form_data':     request.POST,
            })

        keycloak_id = None
        try:
            from authentication.keycloak_admin import KeycloakAdminService
            kc = KeycloakAdminService()
            keycloak_id = kc.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                role=role,
                ministry_schema=ministry_schema or '',
            )
        except Exception as e:
            messages.error(
                request,
                f"Failed to create user in identity server: {str(e)}"
            )
            return render(request, 'authentication/user_form.html', {
                'allowed_roles': allowed_roles,
                'ministries':    ministries,
                'page_title':    'Create New User',
                'form_data':     request.POST,
            })

        try:
            new_user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                ministry_schema=ministry_schema or None,
                keycloak_id=keycloak_id,
            )

            messages.success(
                request,
                f"User '{username}' created successfully in both "
                f"the identity server and the system."
            )
            return redirect('user_list')

        except Exception as e:
            if keycloak_id:
                try:
                    from authentication.keycloak_admin import KeycloakAdminService
                    kc = KeycloakAdminService()
                    kc.delete_user(keycloak_id)
                    logger.warning(
                        f"Rolled back Keycloak user '{username}' "
                        f"after Django creation failed: {e}"
                    )
                except Exception as rollback_error:
                    logger.error(
                        f"Rollback failed for '{username}': {rollback_error}"
                    )

            messages.error(
                request,
                f"User created in identity server but failed in system: "
                f"{str(e)}. The identity server entry has been removed. "
                f"Please try again."
            )
            return render(request, 'authentication/user_form.html', {
                'allowed_roles': allowed_roles,
                'ministries':    ministries,
                'page_title':    'Create New User',
                'form_data':     request.POST,
            })

    return render(request, 'authentication/user_form.html', {
        'allowed_roles': allowed_roles,
        'ministries':    ministries,
        'page_title':    'Create New User',
        'creator_role':  creator.role,
        'form_data':     {},
    })

@login_required_custom
@role_required("SUPER_ADMIN", "MINISTRY_ADMIN", "AGENCY_MANAGER")
def user_edit_view(request, user_id):
    """Edit a user. Enforces security rules — no self-editing, ministry boundaries, role hierarchy."""
    editor = request.user

    # Prevent self-editing
    if editor.id == user_id:
        messages.error(
            request, "You cannot edit your own account here. Use the profile page."
        )
        return redirect("user_list")

    try:
        target_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("user_list")

    # Ministry Admin cannot edit users outside their ministry
    if editor.role == "MINISTRY_ADMIN":
        if target_user.ministry_schema != editor.ministry_schema:
            messages.error(request, "You can only edit users within your own ministry.")
            return redirect("user_list")

    # Agency Manager can only edit Facility Clerks
    if editor.role == "AGENCY_MANAGER":
        if target_user.role != "FACILITY_CLERK":
            messages.error(
                request, "Agency Managers can only edit Facility Clerk accounts."
            )
            return redirect("user_list")

    # Nobody except Super Admin can edit a Super Admin
    if target_user.role == "SUPER_ADMIN" and editor.role != "SUPER_ADMIN":
        messages.error(
            request, "You do not have permission to edit a Super Admin account."
        )
        return redirect("user_list")

    # Determine which roles this editor is allowed to assign
    ASSIGNABLE_ROLES = {
        "SUPER_ADMIN": ["MINISTRY_ADMIN", "SUPER_ADMIN"],
        "MINISTRY_ADMIN": ["AGENCY_MANAGER", "AUDITOR", "FACILITY_CLERK"],
        "AGENCY_MANAGER": ["FACILITY_CLERK"],
    }
    allowed_roles = ASSIGNABLE_ROLES.get(editor.role, [])

    from tenants.models import Ministry

    ministries = Ministry.objects.exclude(schema_name="public")

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        role = request.POST.get("role", target_user.role)
        ministry_schema = request.POST.get(
            "ministry_schema", target_user.ministry_schema
        )

        # Validation
        errors = []
        if not first_name or not last_name:
            errors.append("Full name is required.")
        if role not in allowed_roles:
            errors.append(f"You cannot assign the role {role}.")

        # Ministry Admin can only assign users to their own ministry
        if editor.role == "MINISTRY_ADMIN":
            ministry_schema = editor.ministry_schema

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(
                request,
                "authentication/user_edit.html",
                {
                    "target_user": target_user,
                    "allowed_roles": allowed_roles,
                    "ministries": ministries,
                    "page_title": f"Edit User: {target_user.username}",
                    "editor_role": editor.role,
                },
            )

        # Save changes and write audit log
        try:
            old_role = target_user.role
            old_schema = target_user.ministry_schema

            target_user.first_name      = first_name
            target_user.last_name       = last_name
            target_user.email           = email
            target_user.phone           = phone
            target_user.role            = role
            target_user.ministry_schema = ministry_schema or None
            target_user.save()

            # Sync changes to Keycloak if user is linked
            if target_user.keycloak_id:
                try:
                    from authentication.keycloak_admin import KeycloakAdminService
                    kc = KeycloakAdminService()
                    kc.update_user(
                        keycloak_id=target_user.keycloak_id,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        role=role,
                        ministry_schema=ministry_schema or '',
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"User updated in system but Keycloak sync failed: "
                        f"{str(e)}. The user can still log in."
                    )

            # Write audit log in the target user's ministry schema
            _log_user_action(
                schema_name=target_user.ministry_schema,
                editor=editor,
                action="UPDATE",
                target_user=target_user,
                old_value={"role": old_role, "ministry_schema": old_schema},
                new_value={"role": role, "ministry_schema": ministry_schema},
            )

            messages.success(
                request, f"User '{target_user.username}' updated successfully."
            )
            return redirect("user_list")

        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")

    return render(
        request,
        "authentication/user_edit.html",
        {
            "target_user": target_user,
            "allowed_roles": allowed_roles,
            "ministries": ministries,
            "page_title": f"Edit User: {target_user.username}",
            "editor_role": editor.role,
        },
    )


@login_required_custom
@role_required("SUPER_ADMIN", "MINISTRY_ADMIN")
def user_toggle_active_view(request, user_id):
    """Toggle a user's active status (POST only). No self-deactivation, respects ministry boundaries."""
    editor = request.user

    if request.method != "POST":
        return redirect("user_list")

    # Prevent self-deactivation
    if editor.id == user_id:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("user_list")

    try:
        target_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("user_list")

    # Ministry Admin can only toggle users in their own ministry
    if editor.role == "MINISTRY_ADMIN":
        if target_user.ministry_schema != editor.ministry_schema:
            messages.error(
                request, "You can only manage users within your own ministry."
            )
            return redirect("user_list")

    # Nobody except Super Admin can deactivate a Super Admin
    if target_user.role == "SUPER_ADMIN" and editor.role != "SUPER_ADMIN":
        messages.error(request, "You cannot deactivate a Super Admin account.")
        return redirect("user_list")

    old_status = target_user.is_active

    # Toggle the active status
    target_user.is_active = not target_user.is_active
    target_user.save()

    # Sync active status to Keycloak
    if target_user.keycloak_id:
        try:
            from authentication.keycloak_admin import KeycloakAdminService
            kc = KeycloakAdminService()
            kc.update_user(
                keycloak_id=target_user.keycloak_id,
                is_active=target_user.is_active,
            )
        except Exception as e:
            messages.warning(
                request,
                f"Status updated in system but Keycloak sync failed: "
                f"{str(e)}"
            )

    action_word = "activated" if target_user.is_active else "deactivated"

    # Write audit log
    _log_user_action(
        schema_name=target_user.ministry_schema,
        editor=editor,
        action="UPDATE",
        target_user=target_user,
        old_value={"is_active": old_status},
        new_value={"is_active": target_user.is_active},
    )

    messages.success(request, f"User '{target_user.username}' has been {action_word}.")
    return redirect("user_list")


@login_required_custom
@role_required("SUPER_ADMIN", "MINISTRY_ADMIN")
def user_reset_password_view(request, user_id):
    """Reset a user's password. Ministry Admin can only reset within their own ministry."""
    editor = request.user

    try:
        target_user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("user_list")

    # Ministry Admin can only reset passwords in their own ministry
    if editor.role == "MINISTRY_ADMIN":
        if target_user.ministry_schema != editor.ministry_schema:
            messages.error(
                request, "You can only reset passwords for users in your ministry."
            )
            return redirect("user_list")

    if request.method == "POST":
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            target_user.set_password(new_password)
            target_user.save()

            # Sync new password to Keycloak
            if target_user.keycloak_id:
                try:
                    from authentication.keycloak_admin import KeycloakAdminService
                    kc = KeycloakAdminService()
                    kc.reset_password(
                        keycloak_id=target_user.keycloak_id,
                        new_password=new_password,
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"Password updated in system but Keycloak sync "
                        f"failed: {str(e)}. User may need their password "
                        f"reset again."
                    )

            _log_user_action(
                schema_name=target_user.ministry_schema,
                editor=editor,
                action="UPDATE",
                target_user=target_user,
                old_value={"password": "changed"},
                new_value={"password": "reset by admin"},
            )

            messages.success(
                request, f"Password for '{target_user.username}' reset successfully."
            )
            return redirect("user_list")

    return render(
        request,
        "authentication/user_reset_password.html",
        {
            "target_user": target_user,
            "page_title": f"Reset Password: {target_user.username}",
        },
    )


def _log_user_action(schema_name, editor, action, target_user, old_value, new_value):
    """Write an audit log entry for user management. Skips if schema_name is None (no tenant schema to write to)."""
    if not schema_name:
        return
    try:
        from organizations.models import AuditLog
        from django_tenants.utils import schema_context

        with schema_context(schema_name):
            AuditLog.objects.create(
                performed_by_id=editor.id,
                performed_by_name=editor.get_full_name() or editor.username,
                action=action,
                model_name="CustomUser",
                object_id=str(target_user.id),
                object_repr=str(target_user),
                old_value=old_value,
                new_value=new_value,
            )
    except Exception:
        pass
