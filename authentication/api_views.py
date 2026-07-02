# Purpose: API endpoints for mobile app authentication — login, refresh, profile, verify token, and logout.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django_tenants.utils import schema_context
import logging

from .api_serializers import CustomTokenObtainPairSerializer, UserProfileSerializer

logger = logging.getLogger('authentication')


class LoginAPIView(TokenObtainPairView):
    """POST /api/auth/login/ — verify credentials with brute force protection, return JWT tokens + user profile."""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username   = request.data.get('username', '')
        ip_address = self._get_client_ip(request)

        # ── Check brute force lockout before attempting login ─────────────────
        from authentication.models import LoginAttempt
        is_locked, minutes_left = self._is_locked_out(username, ip_address)

        if is_locked:
            logger.warning(
                f"API Login blocked (locked): {username} from {ip_address}"
            )
            return Response({
                'error':   True,
                'message': (
                    f"Account temporarily locked due to too many failed "
                    f"attempts. Try again in {minutes_left} minute"
                    f"{'s' if minutes_left != 1 else ''}."
                ),
                'code':   'account_locked',
                'status': 429,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # ── Attempt authentication ────────────────────────────────────────────
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Authentication failed — record the attempt
            attempt = self._record_failed_attempt(username, ip_address)

            if attempt.is_locked:
                logger.warning(
                    f"API Login: {username} now locked after "
                    f"{LoginAttempt.MAX_ATTEMPTS} attempts"
                )
                return Response({
                    'error':   True,
                    'message': (
                        f"Too many failed attempts. Account locked for "
                        f"{LoginAttempt.LOCKOUT_MINUTES} minutes."
                    ),
                    'code':   'account_locked',
                    'status': 429,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            remaining = (
                LoginAttempt.MAX_ATTEMPTS - attempt.attempts
            )
            logger.warning(
                f"API Login failed: {username} — "
                f"{remaining} attempts remaining"
            )
            return Response({
                'error':   True,
                'message': (
                    f"Invalid username or password. "
                    f"{remaining} attempt"
                    f"{'s' if remaining != 1 else ''} remaining."
                ),
                'code':   'authentication_required',
                'status': 401,
            }, status=status.HTTP_401_UNAUTHORIZED)

        # ── Successful login ──────────────────────────────────────────────────
        # Clear failed attempts
        self._clear_failed_attempts(username, ip_address)

        user = serializer.user
        logger.info(f"API Login success: {username} from {ip_address}")

        # Record login in audit trail
        if user.ministry_schema:
            try:
                from organizations.models import AuditLog
                with schema_context(user.ministry_schema):
                    AuditLog.objects.create(
                        performed_by_id=user.id,
                        performed_by_name=(
                            user.get_full_name() or user.username
                        ),
                        action='LOGIN',
                        model_name='CustomUser',
                        object_id=str(user.id),
                        object_repr=str(user),
                        ip_address=ip_address,
                        user_agent=request.META.get(
                            'HTTP_USER_AGENT', ''
                        )[:500],
                    )
            except Exception:
                pass

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK
        )

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _is_locked_out(self, username, ip_address):
        from authentication.models import LoginAttempt
        from django.utils import timezone
        try:
            attempt = LoginAttempt.objects.get(
                username=username,
                ip_address=ip_address
            )
            if attempt.locked_until and timezone.now() < attempt.locked_until:
                return True, attempt.minutes_remaining
            if attempt.locked_until and timezone.now() >= attempt.locked_until:
                attempt.attempts     = 0
                attempt.locked_until = None
                attempt.save()
        except LoginAttempt.DoesNotExist:
            pass
        return False, 0

    def _record_failed_attempt(self, username, ip_address):
        from authentication.models import LoginAttempt
        from django.utils import timezone
        from datetime import timedelta

        attempt, _ = LoginAttempt.objects.get_or_create(
            username=username,
            ip_address=ip_address,
            defaults={'attempts': 0}
        )
        if attempt.locked_until and timezone.now() >= attempt.locked_until:
            attempt.attempts     = 0
            attempt.locked_until = None

        attempt.attempts += 1
        if attempt.attempts >= LoginAttempt.MAX_ATTEMPTS:
            attempt.locked_until = (
                timezone.now() +
                timedelta(minutes=LoginAttempt.LOCKOUT_MINUTES)
            )
        attempt.save()
        return attempt

    def _clear_failed_attempts(self, username, ip_address):
        from authentication.models import LoginAttempt
        LoginAttempt.objects.filter(
            username=username,
            ip_address=ip_address
        ).delete()


class RefreshTokenAPIView(APIView):
    """POST /api/auth/refresh/ — exchange a refresh token for a new access token."""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh', '')

        if not refresh_token:
            return Response({
                'error':   True,
                'message': 'Refresh token is required.',
                'code':    'bad_request',
                'status':  400,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)

            # This creates a new access token AND a new refresh token
            # The old refresh token is blacklisted (cannot be used again)
            new_access  = str(token.access_token)
            new_refresh = str(token)

            return Response({
                'access':  new_access,
                'refresh': new_refresh,
            }, status=status.HTTP_200_OK)

        except TokenError as e:
            return Response({
                'error':   True,
                'message': 'Token is invalid or expired. Please log in again.',
                'code':    'authentication_required',
                'status':  401,
            }, status=status.HTTP_401_UNAUTHORIZED)


class MeAPIView(APIView):
    """GET /api/auth/me/ — return the profile of the currently authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerifyTokenAPIView(APIView):
    """GET /api/auth/verify-token/ — other groups call this to validate a token and get user role and ministry."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get ministry name for other groups
        ministry_name = ''
        if user.ministry_schema:
            try:
                from tenants.models import Ministry
                ministry = Ministry.objects.filter(
                    schema_name=user.ministry_schema
                ).first()
                if ministry:
                    ministry_name = ministry.name
            except Exception:
                pass

        return Response({
            'valid': True,
            'user':  {
                'id':              user.id,
                'username':        user.username,
                'full_name':       user.get_full_name() or user.username,
                'email':           user.email or '',
                'role':            user.role,
                'ministry_schema': user.ministry_schema or '',
                'ministry':        ministry_name,
            },
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    """POST /api/auth/logout/ — blacklist the refresh token so it cannot be used again."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh', '')

        if not refresh_token:
            return Response({
                'error':   True,
                'message': 'Refresh token is required.',
                'code':    'bad_request',
                'status':  400,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            # Blacklist this token — it can never be used again
            token.blacklist()

            user = request.user
            logger.info(
                f"API Logout: {user.username} from "
                f"{request.META.get('REMOTE_ADDR', '')}"
            )

            # Record logout in audit trail
            if user.ministry_schema:
                try:
                    from organizations.models import AuditLog
                    with schema_context(user.ministry_schema):
                        AuditLog.objects.create(
                            performed_by_id=user.id,
                            performed_by_name=(
                                user.get_full_name() or user.username
                            ),
                            action='LOGOUT',
                            model_name='CustomUser',
                            object_id=str(user.id),
                            object_repr=str(user),
                            ip_address=request.META.get('REMOTE_ADDR', ''),
                            user_agent=request.META.get(
                                'HTTP_USER_AGENT', ''
                            )[:500],
                        )
                except Exception:
                    pass

            return Response(
                {'message': 'Successfully logged out.'},
                status=status.HTTP_200_OK
            )

        except TokenError:
            return Response({
                'error':   True,
                'message': 'Token is invalid or already expired.',
                'code':    'bad_request',
                'status':  400,
            }, status=status.HTTP_400_BAD_REQUEST)