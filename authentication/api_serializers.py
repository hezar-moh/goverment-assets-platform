# Purpose: Serializers for JWT tokens, user profiles, assets, org units, and audit logs used by the API.

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role, ministry_schema, keycloak_id and full_name to the JWT token so Flutter gets everything in one call."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['ministry_schema'] = user.ministry_schema or ''
        token['keycloak_id'] = user.keycloak_id or ''
        token['full_name'] = user.get_full_name() or user.username
        token['email'] = user.email or ''
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email or '',
            'role': user.role,
            'ministry_schema': user.ministry_schema or '',
        }
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile for the /api/auth/me/ endpoint. Never exposes passwords."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        from authentication.models import CustomUser
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'first_name', 'last_name', 'email',
                  'role', 'ministry_schema', 'phone', 'is_active', 'date_joined']
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AssetCategorySerializer(serializers.Serializer):
    """Asset categories for dropdown menus. Uses Serializer (not ModelSerializer) because it lives in a tenant schema."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    code = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()


class AssetSerializer(serializers.Serializer):
    """All asset fields the Flutter app needs, with computed expiry properties."""
    id = serializers.IntegerField(read_only=True)
    asset_number = serializers.CharField()
    name = serializers.CharField()
    serial_number = serializers.CharField(allow_blank=True, allow_null=True)
    category_id = serializers.IntegerField()
    category_name = serializers.SerializerMethodField()
    category_code = serializers.SerializerMethodField()
    org_unit_id = serializers.IntegerField(allow_null=True)
    org_unit_name = serializers.CharField(allow_blank=True)
    location_type = serializers.CharField(allow_blank=True)
    location_description = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    condition = serializers.CharField()
    manufacturer = serializers.CharField(allow_blank=True)
    model_number = serializers.CharField(allow_blank=True)
    supplier_name = serializers.CharField(allow_blank=True)
    purchase_order_number = serializers.CharField(allow_blank=True)
    acquisition_date = serializers.DateField(allow_null=True)
    warranty_expiry_date = serializers.DateField(allow_null=True)
    asset_expiry_date = serializers.DateField(allow_null=True)
    useful_life_years = serializers.IntegerField(allow_null=True)
    acquisition_cost = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    funding_source = serializers.CharField(allow_blank=True)
    acquisition_method = serializers.CharField(allow_blank=True)
    cost_centre = serializers.CharField(allow_blank=True)
    disposal_method = serializers.CharField(allow_blank=True)
    disposal_date = serializers.DateField(allow_null=True)
    registered_by_name = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        try:
            return obj.category.name
        except Exception:
            return ''

    def get_category_code(self, obj):
        try:
            return obj.category.code
        except Exception:
            return ''

    def get_is_expired(self, obj):
        return obj.is_expired

    def get_expires_soon(self, obj):
        return obj.expires_soon

    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry


class OrgUnitSerializer(serializers.Serializer):
    """Organisation unit for the org tree API."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    code = serializers.CharField(allow_blank=True)
    unit_type = serializers.CharField()
    parent_id = serializers.IntegerField(allow_null=True)
    is_active = serializers.BooleanField()


class AuditLogSerializer(serializers.Serializer):
    """Audit log entries for the API."""
    id = serializers.IntegerField(read_only=True)
    performed_by_id = serializers.IntegerField(allow_null=True)
    performed_by_name = serializers.CharField()
    action = serializers.CharField()
    model_name = serializers.CharField()
    object_id = serializers.CharField(allow_blank=True, allow_null=True)
    object_repr = serializers.CharField(allow_blank=True)
    old_value = serializers.JSONField(allow_null=True)
    new_value = serializers.JSONField(allow_null=True)
    timestamp = serializers.DateTimeField()
    ip_address = serializers.CharField(allow_null=True)