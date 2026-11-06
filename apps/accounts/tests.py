"""
Comprehensive test suite for Accounts application covering Models, Services,
Forms, Views, and Role-Based Access Control.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from .models import CandidateProfile, RecruiterProfile, AuditLog
from .services import (
    UserService,
    AuthenticationService,
    PasswordService,
    AuditLogService,
)
from .utils import role_required, RoleRequiredMixin

User = get_user_model()


class UserModelTests(TestCase):
    """Unit tests for custom User model attributes and role helpers."""

    def test_create_candidate_user(self):
        user = User.objects.create_user(
            username="candidate1",
            email="candidate1@example.com",
            password="StrongPassword123!",
            role=User.Role.CANDIDATE,
        )
        self.assertEqual(user.username, "candidate1")
        self.assertEqual(user.email, "candidate1@example.com")
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertTrue(user.is_candidate)
        self.assertFalse(user.is_recruiter)
        self.assertFalse(user.is_admin_user)
        self.assertFalse(user.is_staff)

    def test_create_recruiter_user(self):
        user = User.objects.create_user(
            username="recruiter1",
            email="recruiter1@example.com",
            password="StrongPassword123!",
            role=User.Role.RECRUITER,
        )
        self.assertTrue(user.is_recruiter)
        self.assertFalse(user.is_candidate)

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            username="admin1",
            email="admin1@example.com",
            password="AdminPassword123!",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.role, User.Role.ADMIN)
        self.assertTrue(admin_user.is_admin_user)


class UserServiceTests(TestCase):
    """Unit tests for user registration, profiles, and state transitions."""

    def test_candidate_registration_creates_profile(self):
        user = UserService.register_user(
            username="john_doe",
            email="john@example.com",
            password="SecurePassword123!",
            role=User.Role.CANDIDATE,
            first_name="John",
            last_name="Doe",
        )
        self.assertIsNotNone(user.pk)
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())
        self.assertFalse(RecruiterProfile.objects.filter(user=user).exists())

    def test_recruiter_registration_creates_profile(self):
        user = UserService.register_user(
            username="jane_hr",
            email="jane@company.com",
            password="SecurePassword123!",
            role=User.Role.RECRUITER,
            first_name="Jane",
            last_name="Recruiter",
        )
        self.assertIsNotNone(user.pk)
        self.assertTrue(RecruiterProfile.objects.filter(user=user).exists())
        self.assertFalse(CandidateProfile.objects.filter(user=user).exists())

    def test_duplicate_registration_raises_validation_error(self):
        UserService.register_user(
            username="testuser",
            email="test@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        with self.assertRaises(ValidationError):
            UserService.register_user(
                username="testuser",
                email="another@example.com",
                password="Password123!",
                role=User.Role.CANDIDATE,
            )

    def test_deactivate_and_activate_user(self):
        user = UserService.register_user(
            username="active_user",
            email="active@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        self.assertTrue(user.is_active)

        UserService.deactivate_user(user, reason="Policy breach")
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        UserService.activate_user(user)
        user.refresh_from_db()
        self.assertTrue(user.is_active)


class AuthenticationServiceTests(TestCase):
    """Unit tests for authentication, sessions, and email logins."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="auth_user",
            email="auth@example.com",
            password="ValidPassword123!",
            role=User.Role.CANDIDATE,
        )

    def _prepare_request(self, path="/accounts/login/"):
        request = self.factory.post(path)
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_authenticate_with_username_success(self):
        request = self._prepare_request()
        user, err = AuthenticationService.authenticate_and_login(request, "auth_user", "ValidPassword123!")
        self.assertIsNotNone(user)
        self.assertIsNone(err)

    def test_authenticate_with_email_success(self):
        request = self._prepare_request()
        user, err = AuthenticationService.authenticate_and_login(request, "auth@example.com", "ValidPassword123!")
        self.assertIsNotNone(user)
        self.assertIsNone(err)

    def test_authenticate_invalid_credentials_fails(self):
        request = self._prepare_request()
        user, err = AuthenticationService.authenticate_and_login(request, "auth_user", "WrongPassword")
        self.assertIsNone(user)
        self.assertIn("Invalid", err)

    def test_authenticate_inactive_user_fails(self):
        self.user.is_active = False
        self.user.save()
        request = self._prepare_request()
        user, err = AuthenticationService.authenticate_and_login(request, "auth_user", "ValidPassword123!")
        self.assertIsNone(user)
        self.assertIn("deactivated", err)


class PasswordServiceTests(TestCase):
    """Unit tests for password changing and reset workflows."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="pwd_user",
            email="pwd@example.com",
            password="OldPassword123!",
            role=User.Role.CANDIDATE,
        )

    def test_change_password_success(self):
        success, msg = PasswordService.change_password(self.user, "OldPassword123!", "NewPassword123!")
        self.assertTrue(success)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_change_password_with_incorrect_old_password_fails(self):
        success, msg = PasswordService.change_password(self.user, "IncorrectOld123!", "NewPassword123!")
        self.assertFalse(success)
        self.assertIn("incorrectly", msg)

    def test_initiate_password_reset_for_valid_email(self):
        result = PasswordService.initiate_password_reset("pwd@example.com")
        self.assertTrue(result)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.PASSWORD_RESET_REQUEST).exists())

    def test_initiate_password_reset_for_unknown_email(self):
        result = PasswordService.initiate_password_reset("unknown@example.com")
        self.assertFalse(result)


class RoleSecurityDecoratorTests(TestCase):
    """Unit tests for role enforcement and permission denial."""

    def setUp(self):
        self.factory = RequestFactory()
        self.candidate = User.objects.create_user(
            username="candidate_sec",
            email="cand_sec@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        self.recruiter = User.objects.create_user(
            username="recruiter_sec",
            email="rec_sec@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
        )

    def test_role_required_permits_authorized_role(self):
        @role_required(["CANDIDATE"])
        def sample_view(request):
            return "OK"

        request = self.factory.get("/")
        request.user = self.candidate
        response = sample_view(request)
        self.assertEqual(response, "OK")

    def test_role_required_blocks_unauthorized_role(self):
        @role_required(["RECRUITER"])
        def sample_view(request):
            return "OK"

        request = self.factory.get("/")
        request.user = self.candidate
        with self.assertRaises(PermissionDenied):
            sample_view(request)

