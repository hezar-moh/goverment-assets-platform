# Purpose: Runs on every request. Sets request.schema_name based on the logged-in user's ministry
# so views and API endpoints know which schema to query.

from django.utils.deprecation import MiddlewareMixin


class SchemaMiddleware(MiddlewareMixin):
    """Attach schema_name and user_role to every request so views know which database schema to use."""

    PUBLIC_PATHS = ['/login/', '/logout/', '/static/', '/admin/']

    def process_request(self, request):
        for path in self.PUBLIC_PATHS:
            if request.path.startswith(path):
                return None

        if hasattr(request, 'user') and request.user.is_authenticated:
            request.schema_name = request.user.ministry_schema or 'public'
            request.user_role = request.user.role
        else:
            request.schema_name = 'public'
            request.user_role = None

        return None