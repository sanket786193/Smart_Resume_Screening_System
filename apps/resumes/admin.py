"""
Django Admin customization for Resumes, Versioning Histories, and Extracted Metadata.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Resume, ResumeHistory


class ResumeHistoryInline(admin.TabularInline):
    model = ResumeHistory
    extra = 0
    readonly_fields = ("version", "file_name", "file_size", "archived_at")
    can_delete = False


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "file_name",
        "version",
        "file_format",
        "is_primary",
        "parsing_status",
        "created_at",
    )
    list_filter = ("parsing_status", "file_format", "is_primary", "created_at")
    search_fields = (
        "candidate__username",
        "candidate__email",
        "file_name",
        "extracted_name",
        "extracted_email",
    )
    readonly_fields = (
        "version",
        "file_size",
        "raw_text",
        "parsing_status",
        "parsing_error",
        "created_at",
        "updated_at",
    )
    inlines = [ResumeHistoryInline]
    ordering = ("-created_at",)


@admin.register(ResumeHistory)
class ResumeHistoryAdmin(admin.ModelAdmin):
    list_display = ("candidate", "file_name", "version", "file_size", "archived_at")
    search_fields = ("candidate__username", "file_name")
    list_filter = ("archived_at",)

