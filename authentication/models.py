# Purpose: Defines CustomUser, PendingAccess, and LoginAttempt models for authentication.

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """Custom user stored in the public schema. Extends Django's built-in user with role, ministry, and Keycloak ID."""

    ROLE_CHOICES = [
        ("SUPER_ADMIN", "Super Admin"),
        ("MINISTRY_ADMIN", "Ministry Admin"),
        ("AGENCY_MANAGER", "Agency Manager"),
        ("FACILITY_CLERK", "Facility Clerk"),
        ("AUDITOR", "Auditor"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="FACILITY_CLERK",
        help_text="Controls what this user can see and do",
    )
    ministry_schema = models.CharField(
        max_length=63,
        blank=True,
        null=True,
        help_text="Which PostgreSQL schema this user belongs to. "
        "Example: moh_schema. Blank for Super Admin.",
    )

    keycloak_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Keycloak user UUID — links this Django account to Keycloak",
    )

    phone = models.CharField(max_length=20, blank=True, null=True)

    # Brute force lockout — separate from is_active so admin deactivation
    # and automatic lockout are distinguishable
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked by brute force protection after too many failed attempts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "authentication"

    def __str__(self):
        return f"{self.get_full_name()} — {self.role}"

    @property
    def is_super_admin(self):
        return self.role == "SUPER_ADMIN"

    @property
    def is_ministry_admin(self):
        return self.role == "MINISTRY_ADMIN"


class PendingAccess(models.Model):
    """Records blocked logins from people who authenticated but have no Django profile yet. Admin reviews and approves or rejects."""

    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    # Who tried to log in
    username = models.CharField(max_length=150, help_text="Username that was attempted")
    email = models.CharField(
        max_length=254, blank=True, help_text="Email if provided during login attempt"
    )
    full_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full name if available from Keycloak token",
    )
    keycloak_id = models.CharField(
        max_length=100, blank=True, help_text="Keycloak user ID if SSO was used"
    )
    ministry_schema = models.CharField(
        max_length=63, blank=True,
        help_text="Which ministry schema this user was trying to access"
    )

    # When and where
    attempted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of the login attempt"
    )
    user_agent = models.CharField(
        max_length=500, blank=True, help_text="Browser or device info"
    )

    # Review status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by_id = models.IntegerField(
        null=True, blank=True, help_text="ID of the admin who reviewed this request"
    )
    reviewed_by_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the admin who reviewed this request",
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True, help_text="When this request was reviewed"
    )
    review_notes = models.TextField(
        blank=True, help_text="Admin notes about this access request"
    )

    class Meta:
        app_label = "authentication"
        ordering = ["-attempted_at"]
        verbose_name = "Pending Access Request"
        verbose_name_plural = "Pending Access Requests"

    def __str__(self):
        return f"{self.username} — {self.status} — {self.attempted_at}"


class LoginAttempt(models.Model):
    """Tracks failed login attempts per username+IP with progressive lockout.

    Stages:
      WARNING  (attempts 1-3): error message only
      COOLDOWN (attempts 4-5): 5-minute temporary lock
      DISABLED (attempts 6+):  account permanently locked (user.is_locked = True)
    """

    STAGE_WARNING  = 'WARNING'
    STAGE_COOLDOWN = 'COOLDOWN'
    STAGE_DISABLED = 'DISABLED'

    username   = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempts   = models.IntegerField(default=0)
    stage      = models.CharField(
        max_length=20,
        default=STAGE_WARNING,
        choices=[
            (STAGE_WARNING,  'Warning'),
            (STAGE_COOLDOWN, 'Cooldown'),
            (STAGE_DISABLED, 'Disabled'),
        ],
    )
    locked_until = models.DateTimeField(
        null=True, blank=True,
        help_text="Temporary cooldown end time — stage 2 only",
    )
    last_attempt = models.DateTimeField(auto_now=True)
    created_at   = models.DateTimeField(
        default=timezone.now,
        help_text="When this attempt record was first created",
    )

    LOCKOUT_MINUTES = 5

    class Meta:
        unique_together = [['username', 'ip_address']]
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'

    def __str__(self):
        return f"{self.username} from {self.ip_address} — {self.attempts} attempts ({self.stage})"

    @property
    def is_locked(self):
        """True if currently in cooldown that has not expired."""
        from django.utils import timezone
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    @property
    def minutes_remaining(self):
        """Minutes left in current cooldown. 0 if not in cooldown."""
        from django.utils import timezone
        if self.locked_until and timezone.now() < self.locked_until:
            delta = self.locked_until - timezone.now()
            return max(1, int(delta.total_seconds() / 60))
        return 0


class UnlockToken(models.Model):
    """One-time email token for self-service account unlock after brute force lockout.

    User receives this in their email — clicking the link proves
    they own the registered email address.
    """

    user       = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='unlock_tokens',
    )
    token      = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used    = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Unlock Token'
        verbose_name_plural = 'Unlock Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Unlock token for {self.user.username} — used: {self.is_used}"

    @property
    def is_valid(self):
        """Token is valid only if not used and not expired."""
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def create_for_user(cls, user, validity_hours=1):
        """Create a fresh one-time unlock token. Invalidates old unused tokens."""
        from django.utils import timezone
        from datetime import timedelta
        cls.objects.filter(user=user, is_used=False).update(
            is_used=True,
            used_at=timezone.now(),
        )
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=validity_hours),
        )



class SuperAdminAuditLog(models.Model):
    """
    Audit log specifically for Super Admin actions that happen
    in the public schema (pending access reviews, ministry creation,
    user creation at platform level).
    
    Lives in the PUBLIC schema since Super Admin has no ministry schema.
    This is a SHARED model in the authentication app.
    """

    ACTION_CHOICES = [
        ('PENDING_APPROVED', 'Pending Access Approved'),
        ('PENDING_REJECTED', 'Pending Access Rejected'),
        ('USER_CREATED',     'User Created'),
        ('USER_DEACTIVATED', 'User Deactivated'),
        ('USER_ACTIVATED',   'User Activated'),
        ('USER_EDITED',      'User Edited'),
        ('MINISTRY_CREATED', 'Ministry Created'),
        ('PASSWORD_RESET',   'Password Reset'),
    ]

    performed_by_id   = models.IntegerField(null=True)
    performed_by_name = models.CharField(max_length=200, blank=True)
    performed_by_role = models.CharField(max_length=50, blank=True)
    action            = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description       = models.TextField(blank=True)
    target_username   = models.CharField(max_length=150, blank=True)
    old_value         = models.JSONField(null=True, blank=True)
    new_value         = models.JSONField(null=True, blank=True)
    ip_address        = models.GenericIPAddressField(null=True, blank=True)
    user_agent        = models.CharField(max_length=500, blank=True)
    timestamp         = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'authentication'
        ordering  = ['-timestamp']
        verbose_name = 'Super Admin Audit Log'

    def __str__(self):
        return f"{self.action} by {self.performed_by_name} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """Tamper-proof — same protection as the tenant AuditLog."""
        if self.pk is not None:
            raise PermissionError(
                "SuperAdminAuditLog records are immutable."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError(
            "SuperAdminAuditLog records cannot be deleted."
        )