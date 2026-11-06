"""
Django Admin customization for Accounts, Profiles, and Immutable Audit Logs.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, CandidateProfile, RecruiterProfile, AuditLog
from .services import AuditLogService


class CandidateProfileInline(admin.StackedInline):
    model = CandidateProfile
    can_delete = False
    verbose_name_plural = "Candidate Specific Profile"
    fk_name = "user"
    extra = 0


class RecruiterProfileInline(admin.StackedInline):
    model = RecruiterProfile
    can_delete = False
    verbose_name_plural = "Recruiter Specific Profile"
    fk_name = "user"
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin interface for enhanced role management and audit awareness."""

    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "is_email_verified",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_active", "is_email_verified", "is_staff", "created_at")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)
    inlines = [CandidateProfileInline, RecruiterProfileInline]
    actions = ["activate_selected_users", "deactivate_selected_users"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "phone_number", "profile_photo", "bio")},
        ),
        (
            _("Roles & Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at", "date_joined", "last_login")

    @admin.action(description=_("Activate selected user accounts"))
    def activate_selected_users(self, request, queryset):
        count = queryset.update(is_active=True)
        for user in queryset:
            AuditLogService.log(
                action=AuditLog.Action.ACCOUNT_ACTIVATED,
                request=request,
                user=user,
                details={"reason": "Bulk admin activation"},
            )
        self.message_user(request, f"{count} user(s) successfully activated.")

    @admin.action(description=_("Deactivate selected user accounts"))
    def deactivate_selected_users(self, request, queryset):
        count = queryset.update(is_active=False)
        for user in queryset:
            AuditLogService.log(
                action=AuditLog.Action.ACCOUNT_DEACTIVATED,
                request=request,
                user=user,
                details={"reason": "Bulk admin deactivation"},
            )
        self.message_user(request, f"{count} user(s) successfully deactivated.")


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "current_job_title", "experience_years", "education_level", "preferred_location")
    search_fields = ("user__username", "user__email", "current_job_title", "preferred_location")
    list_filter = ("education_level",)


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user", "department", "position", "company_size")
    search_fields = ("company_name", "user__username", "user__email", "department")
    list_filter = ("company_size",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin view for regulatory compliance and tamper-proof security auditing."""

    list_display = ("timestamp", "action", "user", "ip_address", "short_agent")
    list_filter = ("action", "timestamp")
    search_fields = ("user__username", "user__email", "action", "ip_address", "user_agent")
    ordering = ("-timestamp",)
    readonly_fields = ("timestamp", "action", "user", "ip_address", "user_agent", "details")

    def short_agent(self, obj):
        return (obj.user_agent[:40] + "...") if obj.user_agent and len(obj.user_agent) > 40 else obj.user_agent
    short_agent.short_description = "User Agent"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

