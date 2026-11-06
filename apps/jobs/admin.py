"""
Django Admin customization for Jobs, Skills, and Required Skill matrices.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Job, Skill, JobRequiredSkill
from .constants import JobStatus


class JobRequiredSkillInline(admin.TabularInline):
    model = JobRequiredSkill
    extra = 1
    autocomplete_fields = ["skill"]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recruiter",
        "job_type",
        "workplace_type",
        "location",
        "status",
        "deadline",
        "views_count",
        "applications_count",
        "created_at",
    )
    list_filter = (
        "status",
        "job_type",
        "workplace_type",
        "education_level",
        "created_at",
    )
    search_fields = (
        "title",
        "recruiter__username",
        "recruiter__email",
        "location",
        "description",
        "skills__name",
    )
    prepopulated_fields = {"slug": ("title", "location")}
    inlines = [JobRequiredSkillInline]
    actions = ["publish_selected_jobs", "close_selected_jobs"]

    @admin.action(description=_("Publish selected jobs (set to Active)"))
    def publish_selected_jobs(self, request, queryset):
        count = queryset.update(status=JobStatus.ACTIVE)
        self.message_user(request, f"{count} job posting(s) successfully activated.")

    @admin.action(description=_("Close selected jobs"))
    def close_selected_jobs(self, request, queryset):
        count = queryset.update(status=JobStatus.CLOSED)
        self.message_user(request, f"{count} job posting(s) marked as closed.")


@admin.register(JobRequiredSkill)
class JobRequiredSkillAdmin(admin.ModelAdmin):
    list_display = ("job", "skill", "is_mandatory", "min_years_experience")
    list_filter = ("is_mandatory",)
    search_fields = ("job__title", "skill__name")

