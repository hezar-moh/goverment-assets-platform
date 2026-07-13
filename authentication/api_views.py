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
    """POST /api/auth/login/ — 3-stage progressive brute force protection.

    Stage 1 (attempts 1-3): WARNING — error message + remaining count
    Stage 2 (attempts 4-5): COOLDOWN — 5-minute lock, warns next = disable
    Stage 3 (attempts 6+):  DISABLED — account permanently locked,
                            unlock email sent to registered email,
                            admin can also unlock from User Management
    """
    serializer_class  = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username   = request.data.get('username', '').strip()
        ip_address = self._get_client_ip(request)
        from django.conf import settings as django_settings
        max_warnings  = getattr(django_settings, 'LOGIN_MAX_WARNINGS',     3)

        # ── Check 1: Is account permanently locked? ─────────────────────────
        try:
            from authentication.models import CustomUser
            user_obj = CustomUser.objects.get(username=username)
            if user_obj.is_locked:
                logger.warning(
                    f"API Login blocked (permanently locked): "
                    f"{username} from {ip_address}"
                )
                return Response({
                    'error':   True,
                    'message': (
                        "Your account has been disabled due to repeated "
                        "failed login attempts. An unlock link has been "
                        "sent to your registered email address. "
                        "If you did not receive it, contact your "
                        "Ministry Administrator."
                    ),
                    'code':   'account_disabled',
                    'status': 403,
                }, status=status.HTTP_403_FORBIDDEN)
        except CustomUser.DoesNotExist:
            pass

        # ── Check 2: Is this IP in temporary cooldown? ──────────────────────
        from authentication.models import LoginAttempt
        cooldown_resp = self._check_cooldown(username, ip_address)
        if cooldown_resp:
            return cooldown_resp

        # ── Attempt authentication ──────────────────────────────────────────
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            result = self._handle_failed_attempt(username, ip_address, request)
            return result

        # ── Success: clear all locks and reset ──────────────────────────────
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

    def _check_cooldown(self, username, ip_address):
        """Return a 429 Response if in cooldown, else None."""
        from authentication.models import LoginAttempt
        try:
            attempt = LoginAttempt.objects.get(
                username=username,
                ip_address=ip_address
            )
            if attempt.is_locked:
                logger.warning(
                    f"API Login blocked (cooldown): "
                    f"{username} from {ip_address}"
                )
                return Response({
                    'error': True,
                    'message': (
                        f"Too many failed attempts. "
                        f"Please wait {attempt.minutes_remaining} minute"
                        f"{'s' if attempt.minutes_remaining != 1 else ''} "
                        f"before trying again."
                    ),
                    'code':   'temp_locked',
                    'status': 429,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except LoginAttempt.DoesNotExist:
            pass
        return None

    def _handle_failed_attempt(self, username, ip_address, request):
        """3-stage progressive lockout logic. Returns the error Response."""
        from authentication.models import LoginAttempt, CustomUser
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings as django_settings

        max_warnings  = getattr(django_settings, 'LOGIN_MAX_WARNINGS',     3)
        max_attempts  = getattr(django_settings, 'LOGIN_MAX_ATTEMPTS',     5)
        cooldown_mins = getattr(django_settings, 'LOGIN_COOLDOWN_MINUTES', 5)

        attempt, _ = LoginAttempt.objects.get_or_create(
            username=username,
            ip_address=ip_address,
            defaults={'attempts': 0, 'stage': LoginAttempt.STAGE_WARNING},
        )

        # If cooldown has expired, we keep counting (don't reset)
        if (attempt.locked_until
                and timezone.now() >= attempt.locked_until):
            attempt.locked_until = None

        attempt.attempts += 1
        attempt.save()

        logger.warning(
            f"API Login failed: {username} from {ip_address} "
            f"— attempt {attempt.attempts}"
        )

        # ── Stage 3: Account permanently disabled ──────────────────────────
        if attempt.attempts > max_attempts:
            self._disable_account(username, ip_address, request, attempt)
            return Response({
                'error': True,
                'message': (
                    "Your account has been disabled for security reasons "
                    "due to repeated failed login attempts. "
                    "An unlock link has been sent to your registered "
                    "email address. If you did not receive it, contact "
                    "your Ministry Administrator."
                ),
                'code':   'account_disabled',
                'status': 403,
            }, status=status.HTTP_403_FORBIDDEN)

        # ── Stage 2: Temporary cooldown ────────────────────────────────────
        if attempt.attempts > max_warnings:
            attempt.stage          = LoginAttempt.STAGE_COOLDOWN
            attempt.locked_until = (
                timezone.now() + timedelta(minutes=cooldown_mins)
            )
            attempt.save()

            remaining = max_attempts - attempt.attempts
            return Response({
                'error': True,
                'message': (
                    f"Incorrect password. "
                    f"Your account will be permanently disabled after "
                    f"{remaining} more failed attempt"
                    f"{'s' if remaining != 1 else ''}. "
                    f"Please wait {cooldown_mins} minutes before "
                    f"trying again."
                ),
                'code':   'temp_locked',
                'status': 429,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # ── Stage 1: Warning only ──────────────────────────────────────────
        remaining = max_attempts - attempt.attempts
        return Response({
            'error': True,
            'message': (
                f"Incorrect username or password. "
                f"{remaining} attempt"
                f"{'s' if remaining != 1 else ''} remaining "
                f"before your account is locked."
            ),
            'code':   'authentication_required',
            'status': 401,
        }, status=status.HTTP_401_UNAUTHORIZED)

    def _disable_account(self, username, ip_address, request, attempt):
        """Permanently lock the user account, send unlock email, write audit log."""
        from authentication.models import CustomUser, UnlockToken

        attempt.stage = LoginAttempt.STAGE_DISABLED
        attempt.save(update_fields=['stage'])

        try:
            user = CustomUser.objects.get(username=username)
            user.is_locked = True
            user.save(update_fields=['is_locked'])

            logger.warning(
                f"SECURITY: Account {username} permanently locked "
                f"after {attempt.attempts} failed attempts from {ip_address}"
            )

            # ── Write audit log ──────────────────────────────────────────
            if user.ministry_schema:
                try:
                    from organizations.models import AuditLog
                    with schema_context(user.ministry_schema):
                        AuditLog.objects.create(
                            performed_by_id=None,
                            performed_by_name='Security System',
                            action='ACCESS_DENIED',
                            model_name='CustomUser',
                            object_id=str(user.id),
                            object_repr=(
                                f"{user.get_full_name() or user.username} "
                                f"— locked by brute force protection"
                            ),
                            ip_address=ip_address,
                            user_agent=request.META.get(
                                'HTTP_USER_AGENT', ''
                            )[:500],
                        )
                except Exception:
                    pass

            # ── Send unlock email ────────────────────────────────────────
            if user.email:
                self._send_unlock_email(user, ip_address)
            else:
                logger.warning(
                    f"Cannot send unlock email to {username} "
                    f"— no email address on record"
                )

        except CustomUser.DoesNotExist:
            logger.error(
                f"Cannot disable account {username} — user not found"
            )

    def _send_unlock_email(self, user, ip_address):
        """Generate an unlock token and email it to the user."""
        from authentication.models import UnlockToken
        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        try:
            token_obj  = UnlockToken.create_for_user(user)
            base_url   = getattr(
                django_settings, 'PLATFORM_BASE_URL',
                'http://localhost:8000'
            )
            unlock_url = f"{base_url}/unlock-account/{token_obj.token}/"

            subject = (
                "GovAsset Platform — Your Account Has Been Locked"
            )
            message = (
                f"Dear {user.get_full_name() or user.username},\n\n"
                f"Your GovAsset Platform account has been locked "
                f"because of too many failed login attempts from "
                f"IP address {ip_address}.\n\n"
                f"If this was you, click the link below to verify "
                f"your identity and unlock your account. This link "
                f"is valid for 1 hour and can only be used once:\n\n"
                f"{unlock_url}\n\n"
                f"If you did not attempt to log in, your password "
                f"may have been compromised. Contact your Ministry "
                f"Administrator immediately after unlocking to "
                f"change your password.\n\n"
                f"GovAsset Platform Security Team"
            )

            send_mail(
                subject=subject,
                message=message,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

            logger.info(
                f"Unlock email sent to {user.email} "
                f"for user {user.username}"
            )

        except Exception as e:
            logger.error(
                f"Failed to send unlock email to {user.username}: {e}"
            )

    def _clear_failed_attempts(self, username, ip_address):
        """Clear all locks on successful login."""
        from authentication.models import LoginAttempt, CustomUser
        LoginAttempt.objects.filter(
            username=username,
            ip_address=ip_address
        ).delete()
        try:
            user = CustomUser.objects.get(username=username)
            if user.is_locked:
                user.is_locked = False
                user.save(update_fields=['is_locked'])
        except CustomUser.DoesNotExist:
            pass

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


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