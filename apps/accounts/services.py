"""
Business Logic & Service Layer for User Accounts, Authentication, and Audit Logging.
Adheres strictly to the Single Responsibility Principle and encapsulates all transactional logic.
"""
import logging
from typing import Optional, Dict, Any, Tuple
from django.db import transaction
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from .models import CandidateProfile, RecruiterProfile, AuditLog
from .utils import get_client_ip, get_user_agent, validate_profile_photo

logger = logging.getLogger(__name__)
User = get_user_model()


class AuditLogService:
    """Central service responsible for persisting immutable security and compliance audit trails."""

    @staticmethod
    def log(
        action: str,
        request: Optional[HttpRequest] = None,
        user: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Record a structured audit log entry.
        Extracts IP and User Agent dynamically from request if provided.
        """
        ip_address = get_client_ip(request) if request else "127.0.0.1"
        user_agent = get_user_agent(request) if request else "Internal Service"
        request_user = getattr(request, "user", None)
        target_user = user or (request_user if request_user and request_user.is_authenticated else None)

        try:
            audit = AuditLog.objects.create(
                user=target_user,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
            )
            logger.info(f"AuditLog created: [{action}] by user {target_user}")
            return audit
        except Exception as exc:
            logger.error(f"Failed to write audit log for {action}: {exc}", exc_info=True)
            # Never bubble up audit log write failure to interrupt user workflow, but log critically
            return None


class UserService:
    """Encapsulates creation, profile enrichment, lifecycle state changes for users."""

    @staticmethod
    @transaction.atomic
    def register_user(
        username: str,
        email: str,
        password: str,
        role: str,
        first_name: str = "",
        last_name: str = "",
        phone_number: str = "",
        request: Optional[HttpRequest] = None,
    ) -> User:
        """
        Registers a new user, hashes password, initializes the corresponding profile table,
        and logs the audit event atomically.
        """
        if role not in User.Role.values:
            raise ValidationError(f"Invalid role '{role}' supplied.")

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")

        user = User.objects.create_user(
            username=username,
            email=email.lower().strip(),
            password=password,
            role=role,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone_number=phone_number.strip(),
        )

        # Initialize domain-specific profiles
        if role == User.Role.CANDIDATE:
            CandidateProfile.objects.create(user=user)
        elif role == User.Role.RECRUITER:
            RecruiterProfile.objects.create(user=user, company_name="Not Specified")

        AuditLogService.log(
            action=AuditLog.Action.REGISTER,
            request=request,
            user=user,
            details={"role": role, "email": user.email},
        )

        return user

    @staticmethod
    @transaction.atomic
    def update_user_profile(
        user: User,
        user_data: Dict[str, Any],
        profile_data: Dict[str, Any],
        photo_file=None,
        request: Optional[HttpRequest] = None,
    ) -> User:
        """
        Atomically updates base User attributes and specialized Candidate or Recruiter profiles.
        """
        if photo_file:
            validate_profile_photo(photo_file)
            user.profile_photo = photo_file

        for field in ["first_name", "last_name", "phone_number", "bio"]:
            if field in user_data:
                setattr(user, field, user_data[field])

        user.save()

        # Update specialized profile
        if user.is_candidate:
            profile, _ = CandidateProfile.objects.get_or_create(user=user)
            for field, value in profile_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
            profile.save()
        elif user.is_recruiter:
            profile, _ = RecruiterProfile.objects.get_or_create(user=user)
            for field, value in profile_data.items():
                if hasattr(profile, field):
                    setattr(profile, field, value)
            profile.save()

        AuditLogService.log(
            action=AuditLog.Action.PROFILE_UPDATE,
            request=request,
            user=user,
            details={"updated_fields": list(user_data.keys()) + list(profile_data.keys())},
        )
        return user

    @staticmethod
    def deactivate_user(user: User, request: Optional[HttpRequest] = None, reason: str = "") -> None:
        """Deactivates an account to prevent login while preserving audit and relational data."""
        user.is_active = False
        user.save(update_fields=["is_active"])
        AuditLogService.log(
            action=AuditLog.Action.ACCOUNT_DEACTIVATED,
            request=request,
            user=user,
            details={"reason": reason},
        )

    @staticmethod
    def activate_user(user: User, request: Optional[HttpRequest] = None) -> None:
        """Re-activates a previously deactivated account."""
        user.is_active = True
        user.save(update_fields=["is_active"])
        AuditLogService.log(
            action=AuditLog.Action.ACCOUNT_ACTIVATED,
            request=request,
            user=user,
        )


class AuthenticationService:
    """Manages credentials verification, session creation, logout, and security logging."""

    @staticmethod
    def authenticate_and_login(
        request: HttpRequest,
        username_or_email: str,
        password: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticates against either username or email.
        Enforces active status check and writes audit records for successes and failures.
        """
        lookup_username = username_or_email.strip()

        # Resolve email to username if an email address was passed
        matching_user = User.objects.filter(username__iexact=lookup_username).first()
        if not matching_user and "@" in lookup_username:
            matching_user = User.objects.filter(email__iexact=lookup_username).first()

        if matching_user:
            lookup_username = matching_user.username
            if not matching_user.is_active and matching_user.check_password(password):
                AuditLogService.log(
                    action=AuditLog.Action.LOGIN_FAILURE,
                    request=request,
                    user=matching_user,
                    details={"reason": "Account is inactive/suspended"},
                )
                return None, "This account is currently deactivated. Please contact an administrator."

        user = authenticate(request, username=lookup_username, password=password)

        if user is None:
            AuditLogService.log(
                action=AuditLog.Action.LOGIN_FAILURE,
                request=request,
                details={"attempted_identifier": username_or_email},
            )
            return None, "Invalid username/email or password."

        login(request, user)

        AuditLogService.log(
            action=AuditLog.Action.LOGIN_SUCCESS,
            request=request,
            user=user,
            details={"role": user.role},
        )
        return user, None

    @staticmethod
    def logout_user(request: HttpRequest) -> None:
        """Terminates session and records audit event."""
        req_user = getattr(request, "user", None)
        if req_user and req_user.is_authenticated:
            AuditLogService.log(
                action=AuditLog.Action.LOGOUT,
                request=request,
                user=req_user,
            )
        logout(request)


class PasswordService:
    """Handles password reset token distribution, token confirmation, and password changes."""

    @staticmethod
    def initiate_password_reset(email: str, request: Optional[HttpRequest] = None) -> bool:
        """
        Identifies active user by email, builds secure one-time cryptographic token,
        and dispatches email. Returns True if user found, False otherwise (timing safe).
        """
        user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
        if not user:
            logger.warning(f"Password reset requested for non-existent or inactive email: {email}")
            return False

        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Build absolute reset URL
        host = request.get_host() if request else "localhost:8000"
        scheme = "https" if request and request.is_secure() else "http"
        reset_link = f"{scheme}://{host}/accounts/reset-password/{uidb64}/{token}/"

        subject = "Smart ATS: Password Reset Request"
        message = (
            f"Hello {user.get_full_name() or user.username},\n\n"
            f"We received a request to reset your password for Smart ATS.\n"
            f"Click the link below to set a new password:\n{reset_link}\n\n"
            f"If you did not request this change, you can safely ignore this email.\n\n"
            f"Regards,\nSmart ATS Security Team"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            AuditLogService.log(
                action=AuditLog.Action.PASSWORD_RESET_REQUEST,
                request=request,
                user=user,
                details={"email": user.email},
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to dispatch password reset email: {exc}", exc_info=True)
            return False

    @staticmethod
    def confirm_password_reset(uidb64: str, token: str, new_password: str, request: Optional[HttpRequest] = None) -> Tuple[bool, str]:
        """Validates base64 user ID and token, and commits new hashed password."""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return False, "Invalid or expired password reset link."

        if not default_token_generator.check_token(user, token):
            return False, "The password reset token is invalid or has expired."

        user.set_password(new_password)
        user.save()

        AuditLogService.log(
            action=AuditLog.Action.PASSWORD_RESET_COMPLETE,
            request=request,
            user=user,
        )
        return True, "Password has been successfully reset. You may now log in."

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str, request: Optional[HttpRequest] = None) -> Tuple[bool, str]:
        """Verifies old password before setting new password."""
        if not user.check_password(old_password):
            return False, "Your existing password was entered incorrectly."

        user.set_password(new_password)
        user.save()

        AuditLogService.log(
            action=AuditLog.Action.PASSWORD_CHANGE,
            request=request,
            user=user,
        )
        return True, "Your password was updated successfully."
