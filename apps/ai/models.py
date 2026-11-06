"""AI models for ATS score and resume-job analysis results."""
from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from ai.constants import (
    SCORE_MIN,
    TIER_HIGH_THRESHOLD,
    TIER_LOW_LABEL,
    TIER_MEDIUM_THRESHOLD,
    TIER_MODERATE_LABEL,
    TIER_STRONG_LABEL,
)
from ai.validators import validate_score_range


class ATSAnalysisResult(models.Model):
    """Stores the calculated ATS score, matching metrics, and AI recommendations."""

    resume = models.ForeignKey(
        "resumes.Resume",
        on_delete=models.CASCADE,
        related_name="ats_evaluations",
        verbose_name=_("Resume"),
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="ats_evaluations",
        verbose_name=_("Job"),
    )
    overall_score = models.DecimalField(
        _("Overall ATS Score"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
        help_text=_("Final ATS score from 0.00 to 100.00"),
    )
    match_percentage = models.DecimalField(
        _("Cosine / Semantic Match %"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    skills_score = models.DecimalField(
        _("Skills Score (Weight 40%)"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    experience_score = models.DecimalField(
        _("Experience Score (Weight 25%)"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    education_score = models.DecimalField(
        _("Education Score (Weight 15%)"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    projects_score = models.DecimalField(
        _("Projects Score (Weight 10%)"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    certifications_score = models.DecimalField(
        _("Certifications Score (Weight 10%)"),
        max_digits=5,
        decimal_places=2,
        default=SCORE_MIN,
        validators=[validate_score_range],
    )
    matched_skills = models.JSONField(
        _("Matched Skills"),
        default=list,
        blank=True,
    )
    missing_skills = models.JSONField(
        _("Missing Required Skills"),
        default=list,
        blank=True,
    )
    suggested_skills = models.JSONField(
        _("Suggested / Preferred Skills"),
        default=list,
        blank=True,
    )
    recommendations = models.JSONField(
        _("AI Recommendations"),
        default=list,
        blank=True,
    )
    summary = models.TextField(
        _("Analysis Summary"),
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_ats_analysis_results"
        verbose_name = _("ATS Analysis Result")
        verbose_name_plural = _("ATS Analysis Results")
        unique_together = ("resume", "job")
        ordering = ["-overall_score", "-created_at"]
        indexes = [
            models.Index(fields=["job", "-overall_score"], name="idx_ai_job_score"),
            models.Index(fields=["resume", "job"], name="idx_ai_resume_job"),
        ]

    def __str__(self) -> str:
        user = getattr(self.resume, "candidate", getattr(self.resume, "user", None))
        email = user.email if user else "Unknown"
        return f"{email} - {self.job.title} ({self.overall_score}%)"

    @property
    def candidate_user(self):
        """Retrieve owning user account."""
        return getattr(self.resume, "candidate", getattr(self.resume, "user", None))

    @property
    def tier(self) -> str:
        """Return candidate suitability tier."""
        score = float(self.overall_score)
        if score >= TIER_HIGH_THRESHOLD:
            return TIER_STRONG_LABEL
        if score >= TIER_MEDIUM_THRESHOLD:
            return TIER_MODERATE_LABEL
        return TIER_LOW_LABEL
