"""Models for organisational hierarchy, master data, and audit logging."""
from django.db import models


class OrgUnit(models.Model):
    """Three-level hierarchy: MINISTRY → AGENCY → FACILITY via self-referencing parent FK."""

    UNIT_TYPE_CHOICES = [
        ('MINISTRY', 'Ministry'),
        ('AGENCY', 'Agency'),
        ('FACILITY', 'Facility'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Short code for this unit. Example: MOH, MNH, RAD"
    )
    unit_type = models.CharField(
        max_length=20,
        choices=UNIT_TYPE_CHOICES,
        help_text="Level in the hierarchy"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='children',
        help_text="Parent unit. Null only for the root Ministry."
    )
    manager_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the CustomUser who manages this unit"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'organizations'
        verbose_name = 'Organisation Unit'
        verbose_name_plural = 'Organisation Units'

    def __str__(self):
        return f"{self.name} ({self.unit_type})"

    def get_full_path(self):
        """Full path from root to this unit. Example: Ministry of Health > Muhimbili > Radiology"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class MasterData(models.Model):
    """Configurable reference data per ministry (funding sources, location types, etc.) so admins can manage dropdown options without code changes."""

    CATEGORY_CHOICES = [
        ('FUNDING_SOURCE',     'Funding Source'),
        ('ACQUISITION_METHOD', 'Acquisition Method'),
        ('LOCATION_TYPE',      'Location Type'),
        ('DISPOSAL_METHOD',    'Disposal Method'),
        ('COST_CENTRE',        'Cost Centre'),
    ]

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        help_text="Which type of reference data this is"
    )
    value = models.CharField(
        max_length=100,
        help_text="The stored code value. Example: GOVT"
    )
    label = models.CharField(
        max_length=200,
        help_text="Human-readable display label. Example: Government Budget"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(
        default=0,
        help_text="Controls display order in dropdowns"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'organizations'
        ordering = ['category', 'sort_order', 'label']
        unique_together = [['category', 'value']]
        verbose_name = 'Master Data'
        verbose_name_plural = 'Master Data'

    def __str__(self):
        return f"{self.category}: {self.label}"
    

class AuditLog(models.Model):
    """Tamper-proof record of every action — lives in each ministry's private schema. CREATE/UPDATE/DELETE/LOGIN/LOGOUT/ACCESS_DENIED."""

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ACCESS_DENIED', 'Access Denied'),
    ]

    performed_by_id = models.IntegerField(
        null=True,
        help_text="ID of the CustomUser who performed this action"
    )
    performed_by_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full name snapshot — preserved even if user is deleted"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True, null=True)
    object_repr = models.CharField(max_length=300, blank=True)
    old_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Values BEFORE the change. Null for CREATE actions."
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Values AFTER the change. Null for DELETE actions."
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        app_label = 'organizations'
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.action} on {self.model_name} by {self.performed_by_name}"

    def save(self, *args, **kwargs):
        """Block editing of existing records — tamper-proof."""
        if self.pk is not None:
            raise PermissionError(
                "AuditLog records are immutable and cannot be modified."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Block all deletion — the audit trail is permanent."""
        raise PermissionError(
            "AuditLog records cannot be deleted."
        )
    
    @classmethod
    def admin_bulk_delete(cls):
        """Bulk delete all audit logs for data reset purposes (management commands only)."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM "{cls._meta.db_table}"'
            )
    
    