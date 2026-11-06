"""
Utility helpers, security decorators, and validation utilities for Accounts.
"""
from functools import wraps
from typing import Sequence, Callable
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from PIL import Image


def get_client_ip(request: HttpRequest) -> str:
    """Safely resolve the client IP address considering proxy headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    return ip


def get_user_agent(request: HttpRequest) -> str:
    """Extract and truncate user-agent string."""
    return request.META.get("HTTP_USER_AGENT", "")[:500]


def role_required(allowed_roles: Sequence[str]):
    """
    Decorator for views that checks if the logged-in user possesses one of the allowed roles.
    Raises PermissionDenied (403) or redirects unauthenticated users to login.
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            user_role = getattr(request.user, "role", None)
            # Superuser always bypasses role restriction for administrative oversight
            if request.user.is_superuser or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("You do not have access to this resource.")

        return _wrapped_view
    return decorator


def candidate_required(view_func: Callable):
    """Enforce Candidate role."""
    return role_required(["CANDIDATE"])(view_func)


def recruiter_required(view_func: Callable):
    """Enforce Recruiter role."""
    return role_required(["RECRUITER"])(view_func)


def admin_required(view_func: Callable):
    """Enforce Admin role."""
    return role_required(["ADMIN"])(view_func)


class RoleRequiredMixin:
    """
    CBV Mixin to restrict view access by User role.
    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = ['RECRUITER', 'ADMIN']
    """
    allowed_roles: Sequence[str] = ()

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        user_role = getattr(request.user, "role", None)
        if request.user.is_superuser or user_role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)

        raise PermissionDenied("You do not have permission to view this page.")


def validate_profile_photo(photo_file):
    """
    Validates uploaded profile image:
    1. Size limit (max 5 MB)
    2. File format (JPEG, PNG, WEBP)
    3. Structural image integrity via Pillow
    """
    if not photo_file:
        return

    max_size_bytes = 5 * 1024 * 1024  # 5MB
    if photo_file.size > max_size_bytes:
        raise ValidationError(f"Image file size cannot exceed 5MB. Uploaded size: {photo_file.size / (1024*1024):.2f}MB.")

    valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
    name_lower = photo_file.name.lower()
    if not any(name_lower.endswith(ext) for ext in valid_extensions):
        raise ValidationError("Unsupported image format. Allowed formats: JPG, PNG, WEBP.")

    try:
        photo_file.seek(0)
        img = Image.open(photo_file)
        img.verify()
        photo_file.seek(0)
    except Exception as exc:
        raise ValidationError("Uploaded file is corrupted or not a valid image.") from exc

