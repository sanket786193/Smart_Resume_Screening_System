"""
Thin view controllers for Accounts application.
Delegates all state transitions, validations, and business logic to services.py.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, HttpRequest, HttpResponseForbidden
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserProfileUpdateForm,
    CandidateProfileForm,
    RecruiterProfileForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    CustomPasswordChangeForm,
)
from .services import (
    UserService,
    AuthenticationService,
    PasswordService,
    AuditLogService,
)
from .models import AuditLog, User
from .utils import RoleRequiredMixin, admin_required

logger = logging.getLogger(__name__)


class RegisterView(View):
    """Handles new Candidate and Recruiter onboarding."""

    template_name = "accounts/register.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        form = UserRegistrationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:home")

        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                user = UserService.register_user(
                    username=cleaned["username"],
                    email=cleaned["email"],
                    password=cleaned["password"],
                    role=cleaned["role"],
                    first_name=cleaned.get("first_name", ""),
                    last_name=cleaned.get("last_name", ""),
                    phone_number=cleaned.get("phone_number", ""),
                    request=request,
                )
                messages.success(request, "Registration successful! You can now log in.")
                return redirect("accounts:login")
            except Exception as exc:
                logger.error(f"Registration failure: {exc}", exc_info=True)
                messages.error(request, f"Registration failed: {exc}")

        return render(request, self.template_name, {"form": form})


class LoginView(View):
    """Authenticates users and starts active session."""

    template_name = "accounts/login.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        form = UserLoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("dashboard:home")

        form = UserLoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data["username_or_email"]
            password = form.cleaned_data["password"]

            user, error_msg = AuthenticationService.authenticate_and_login(
                request=request,
                username_or_email=username_or_email,
                password=password,
            )
            if user:
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("dashboard:home")
            else:
                messages.error(request, error_msg or "Invalid credentials.")

        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    """Ends user session and directs to login."""

    def post(self, request: HttpRequest) -> HttpResponse:
        AuthenticationService.logout_user(request)
        messages.info(request, "You have been logged out successfully.")
        return redirect("accounts:login")

    def get(self, request: HttpRequest) -> HttpResponse:
        # Standard fallback for GET navigation
        return self.post(request)


class ForgotPasswordView(View):
    """Initiates secure password reset token delivery via email."""

    template_name = "accounts/forgot_password.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = CustomPasswordResetForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            # Service gracefully handles non-existent emails without leaking existence
            PasswordService.initiate_password_reset(email, request=request)
            messages.info(
                request,
                "If an account exists with this email, you will receive password reset instructions shortly.",
            )
            return redirect("accounts:login")

        return render(request, self.template_name, {"form": form})


class ResetPasswordConfirmView(View):
    """Verifies reset token and updates password."""

    template_name = "accounts/reset_password_confirm.html"

    def get(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        form = CustomSetPasswordForm()
        return render(request, self.template_name, {"form": form, "uidb64": uidb64, "token": token})

    def post(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        form = CustomSetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            success, message = PasswordService.confirm_password_reset(
                uidb64=uidb64,
                token=token,
                new_password=new_password,
                request=request,
            )
            if success:
                messages.success(request, message)
                return redirect("accounts:login")
            else:
                messages.error(request, message)

        return render(request, self.template_name, {"form": form, "uidb64": uidb64, "token": token})


class ChangePasswordView(LoginRequiredMixin, View):
    """Allows an authenticated user to alter their active password."""

    template_name = "accounts/change_password.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = CustomPasswordChangeForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = CustomPasswordChangeForm(request.POST)
        if form.is_valid():
            old_password = form.cleaned_data["old_password"]
            new_password = form.cleaned_data["new_password"]

            success, message = PasswordService.change_password(
                user=request.user,
                old_password=old_password,
                new_password=new_password,
                request=request,
            )
            if success:
                # Keep user logged in after password rotation
                update_session_auth_hash(request, request.user)
                messages.success(request, message)
                return redirect("accounts:profile")
            else:
                messages.error(request, message)

        return render(request, self.template_name, {"form": form})


class ProfileUpdateView(LoginRequiredMixin, View):
    """Allows user to inspect and edit base details and role-specific profile fields."""

    template_name = "accounts/profile.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        user_form = UserProfileUpdateForm(instance=user)
        profile_form = None

        if user.is_candidate and hasattr(user, "candidate_profile"):
            profile_form = CandidateProfileForm(instance=user.candidate_profile)
        elif user.is_recruiter and hasattr(user, "recruiter_profile"):
            profile_form = RecruiterProfileForm(instance=user.recruiter_profile)

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        user_form = UserProfileUpdateForm(request.POST, request.FILES, instance=user)
        profile_form = None

        if user.is_candidate:
            profile_form = CandidateProfileForm(
                request.POST,
                instance=getattr(user, "candidate_profile", None),
            )
        elif user.is_recruiter:
            profile_form = RecruiterProfileForm(
                request.POST,
                instance=getattr(user, "recruiter_profile", None),
            )

        is_user_valid = user_form.is_valid()
        is_profile_valid = profile_form.is_valid() if profile_form else True

        if is_user_valid and is_profile_valid:
            try:
                UserService.update_user_profile(
                    user=user,
                    user_data=user_form.cleaned_data,
                    profile_data=profile_form.cleaned_data if profile_form else {},
                    photo_file=request.FILES.get("profile_photo"),
                    request=request,
                )
                messages.success(request, "Your profile has been updated successfully.")
                return redirect("accounts:profile")
            except Exception as exc:
                logger.error(f"Profile update error: {exc}", exc_info=True)
                messages.error(request, f"Could not update profile: {exc}")

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )


class UserDeactivateView(LoginRequiredMixin, View):
    """Allows a user to self-deactivate their account."""

    def post(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        reason = request.POST.get("reason", "Voluntary user deactivation")
        UserService.deactivate_user(user=user, request=request, reason=reason)
        AuthenticationService.logout_user(request)
        messages.warning(request, "Your account has been deactivated.")
        return redirect("accounts:login")


class AuditLogListView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Audit log viewer reserved exclusively for platform Administrators."""

    allowed_roles = ["ADMIN"]
    template_name = "accounts/audit_logs.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        action_filter = request.GET.get("action")
        username_filter = request.GET.get("username")

        logs_qs = AuditLog.objects.select_related("user").all()

        if action_filter:
            logs_qs = logs_qs.filter(action=action_filter)
        if username_filter:
            logs_qs = logs_qs.filter(user__username__icontains=username_filter)

        paginator = Paginator(logs_qs, 25)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "actions": AuditLog.Action.choices,
            "selected_action": action_filter,
            "selected_username": username_filter,
        }
        return render(request, self.template_name, context)


# ==========================================
# Custom HTTP Error Handlers
# ==========================================
def custom_permission_denied_view(request: HttpRequest, exception=None) -> HttpResponseForbidden:
    return render(request, "403.html", {"exception": str(exception)}, status=403)


def custom_page_not_found_view(request: HttpRequest, exception=None) -> HttpResponse:
    return render(request, "404.html", status=404)


def custom_server_error_view(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)

