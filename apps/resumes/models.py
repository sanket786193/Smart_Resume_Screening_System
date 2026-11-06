"""
Database models for Candidate Resumes, Versioning History, and Extracted Intelligence.
"""
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .constants import ParsingStatus, ResumeFormat
from .validators import validate_resume_file


class Resume(models.Model):
    """Candidate uploaded resume document containing extracted semantic metadata."""

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
        limit_choices_to={"role": "CANDIDATE"},
        help_text=_("The candidate who owns this resume document."),
    )
    file = models.FileField(
        upload_to="resumes/%Y/%m/",
        validators=[validate_resume_file],
        help_text=_("Resume file in PDF or DOCX format (Max 10 MB)."),
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text=_("File size in bytes."))
    file_format = models.CharField(max_length=10, choices=ResumeFormat.choices)
    version = models.PositiveIntegerField(default=1, help_text=_("Incremental version number."))
    is_primary = models.BooleanField(
        default=True,
        help_text=_("Designates the active default resume used for fast 1-click applications."),
    )
    raw_text = models.TextField(blank=True, default="", help_text=_("Full extracted textual corpus."))

    # Extracted Intelligence
    extracted_name = models.CharField(max_length=150, blank=True, default="")
    extracted_email = models.CharField(max_length=150, blank=True, default="")
    extracted_phone = models.CharField(max_length=50, blank=True, default="")
    extracted_skills = models.JSONField(default=list, blank=True, help_text=_("Extracted technical and soft skills."))
    extracted_education = models.JSONField(default=list, blank=True, help_text=_("Educational degrees and institutions."))
    extracted_experience = models.JSONField(default=list, blank=True, help_text=_("Work positions, employers, and durations."))
    extracted_projects = models.JSONField(default=list, blank=True, help_text=_("Technical projects, repos, and descriptions."))
    extracted_certifications = models.JSONField(default=list, blank=True, help_text=_("Professional credentials and licenses."))
    extracted_languages = models.JSONField(default=list, blank=True, help_text=_("Natural languages spoken/written."))
    extracted_github = models.CharField(max_length=255, blank=True, default="")
    extracted_linkedin = models.CharField(max_length=255, blank=True, default="")

    parsing_status = models.CharField(
        max_length=20,
        choices=ParsingStatus.choices,
        default=ParsingStatus.PENDING,
        db_index=True,
    )
    parsing_error = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Resume")
        verbose_name_plural = _("Resumes")
        ordering = ["-is_primary", "-updated_at"]
        indexes = [
            models.Index(fields=["candidate", "is_primary"]),
            models.Index(fields=["parsing_status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.candidate.get_full_name() or self.candidate.username} - v{self.version} ({self.file_name})"

    @property
    def file_size_display(self) -> str:
        """Human-readable size format."""
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.2f} MB"


class ResumeHistory(models.Model):
    """Archived snapshots of superseded resume versions for auditability."""

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resume_archives",
    )
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="history_records",
    )
    file = models.FileField(upload_to="resumes/history/%Y/%m/")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    version = models.PositiveIntegerField()
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Resume History")
        verbose_name_plural = _("Resume Histories")
        ordering = ["-version"]

    def __str__(self):
        return f"Archive v{self.version} of {self.file_name} ({self.candidate.username})"

