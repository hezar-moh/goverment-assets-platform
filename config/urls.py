from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="GovAsset Platform API",
        default_version='v1',
        description=(
            "REST API for the Government Asset Management Platform.\n\n"
            "## How to authenticate\n"
            "1. Call POST /api/auth/login/ with username and password\n"
            "2. Copy the 'access' token from the response\n"
            "3. Click the Authorize button and enter: Bearer {your_token}\n"
            "4. All requests will now include the token automatically\n\n"
            "## For Groups 2-10\n"
            "Call GET /api/auth/verify-token/ with the user's Bearer token "
            "to validate it and get role and ministry_schema."
        ),
        contact=openapi.Contact(email="admin@platform.go.tz"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('', include('dashboard.urls')),
    path('', include('assets.urls')),
    path('', include('organizations.urls')),
    path('', include('tenants.urls')),
    path(
        'api/docs/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'
    ),
    path(
        'api/redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'
    ),
    path('api/', include('api.urls')),
    path('oidc/', include('mozilla_django_oidc.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
