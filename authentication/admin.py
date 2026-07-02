# Purpose: Register CustomUser with Django admin so Super Admin can manage users.

from django.contrib import admin
from .models import CustomUser

admin.site.register(CustomUser)