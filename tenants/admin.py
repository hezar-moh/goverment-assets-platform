"""Admin registration for Ministry and Domain models."""
from django.contrib import admin
from .models import Ministry, Domain

admin.site.register(Ministry)
admin.site.register(Domain)