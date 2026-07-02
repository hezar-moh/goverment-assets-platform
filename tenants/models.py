"""Models for multi-tenant ministries using django-tenants."""
from django_tenants.models import TenantMixin, DomainMixin
from django.db import models


class Ministry(TenantMixin):
    """One government ministry = one tenant = one PostgreSQL schema. TenantMixin provides schema_name."""

    name = models.CharField(max_length=200, help_text="Full ministry name")
    short_name = models.CharField(max_length=50, help_text="Abbreviation e.g. MOH")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    auto_create_schema = True

    class Meta:
        app_label = 'tenants'
        verbose_name_plural = 'Ministries'
        # currently the table name will be tenants_domain but you
        # can change it by add the code below in meta here
        #db_name = 'ministries'

    def __str__(self):
        return f"{self.name} ({self.schema_name})"


class Domain(DomainMixin):
    """Maps a domain (e.g. moh.localhost) to a Ministry. DomainMixin provides domain, tenant, is_primary fields."""

    class Meta:
        app_label = 'tenants'
        # currently the table name will be tenants_domain but you
        # can change it by add the code below in meta here
        #db_name = 'tenats'

    def __str__(self):
        return self.domain