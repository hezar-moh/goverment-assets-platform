# Purpose: Defines CustomUser, PendingAccess, and LoginAttempt models for authentication.

from django.contrib.auth.models import AbstractUser
from django.db import models


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
    """Tracks failed logins per username+IP. Locks the account after 5 failed attempts for 15 minutes."""

    MAX_ATTEMPTS = 5  # Failed attempts before lockout
    LOCKOUT_MINUTES = 15  # How long the lockout lasts

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time. Null means not locked.",
    )

    class Meta:
        app_label = "authentication"
        unique_together = [["username", "ip_address"]]
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"

    def __str__(self):
        return f"{self.username} — {self.attempts} attempts"

    @property
    def is_locked(self):
        """Whether this username+IP is currently locked out."""
        if self.locked_until:
            from django.utils import timezone

            return timezone.now() < self.locked_until
        return False

    @property
    def minutes_remaining(self):
        """Minutes left in the lockout. Returns 0 if not locked."""
        if self.is_locked:
            from django.utils import timezone

            delta = self.locked_until - timezone.now()
            return max(1, int(delta.total_seconds() / 60))
        return 0
