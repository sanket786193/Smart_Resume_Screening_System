"""Django Admin configuration for AI ATS evaluations."""
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from ai.models import ATSAnalysisResult


@admin.register(ATSAnalysisResult)
class ATSAnalysisResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "resume_link",
        "job_link",
        "score_badge",
        "match_percentage",
        "tier",
        "created_at",
    )
    list_filter = ("created_at", "job")
    search_fields = (
        "resume__candidate__email",
        "resume__candidate__username",
        "job__title",
        "matched_skills",
        "missing_skills",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "overall_score",
        "match_percentage",
        "skills_score",
        "experience_score",
        "education_score",
        "projects_score",
        "certifications_score",
    )

    def resume_link(self, obj: ATSAnalysisResult) -> str:
        user = getattr(obj.resume, "candidate", getattr(obj.resume, "user", None))
        email = user.email if user else "Unknown"
        return f"{email} (ID: {obj.resume.id})"
    resume_link.short_description = "Resume"

    def job_link(self, obj: ATSAnalysisResult) -> str:
        return obj.job.title
    job_link.short_description = "Target Job"

    def score_badge(self, obj: ATSAnalysisResult) -> str:
        score = float(obj.overall_score)
        if score >= 80:
            color = "#059669"
        elif score >= 60:
            color = "#d97706"
        else:
            color = "#dc2626"
        return format_html(
            '<span style="font-weight:700; color:{}; padding:3px 8px; border-radius:4px; background:#f3f4f6;">{}%</span>',
            color,
            score,
        )
    score_badge.short_description = "ATS Score"
