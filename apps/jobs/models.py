"""
Models for the Jobs application.
Includes normalized Skill repository, Job listings, and Required Skill linkages.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone

from .constants import (
    JobType,
    WorkplaceType,
    JobStatus,
    EducationLevel,
    DEFAULT_CURRENCY,
    CURRENCY_CHOICES,
)
from .validators import validate_future_deadline


class Skill(models.Model):
    """Normalized technical and professional skill entity."""

    CATEGORY_CHOICES = [
        ("PROGRAMMING", _("Programming Language")),
        ("FRAMEWORK", _("Framework / Library")),
        ("DATABASE", _("Database / Datastore")),
        ("CLOUD_DEVOPS", _("Cloud & DevOps")),
        ("DATA_AI", _("Data Science & Machine Learning")),
        ("TESTING", _("Testing & QA")),
        ("DESIGN", _("UI/UX & Product Design")),
        ("SOFT_SKILL", _("Soft Skill / Leadership")),
        ("OTHER", _("Other Technical Competency")),
    ]

    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="OTHER")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Job(models.Model):
    """Core Job opening entity published and managed by Recruiters."""

    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posted_jobs",
        limit_choices_to={"role": "RECRUITER"},
        help_text=_("The recruiter or employer responsible for this job posting."),
    )
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    department = models.CharField(max_length=120, blank=True, null=True, help_text=_("e.g. Engineering, Sales, Product"))
    description = models.TextField(help_text=_("Comprehensive job overview and contextual background."))
    responsibilities = models.TextField(blank=True, null=True, help_text=_("Day-to-day duties and core deliverables."))
    requirements = models.TextField(blank=True, null=True, help_text=_("Must-have qualifications and competencies."))
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.FULL_TIME,
        db_index=True,
    )
    workplace_type = models.CharField(
        max_length=20,
        choices=WorkplaceType.choices,
        default=WorkplaceType.ON_SITE,
        db_index=True,
    )
    experience_min = models.PositiveIntegerField(
        default=0,
        help_text=_("Minimum required professional experience in years."),
    )
    experience_max = models.PositiveIntegerField(
        default=2,
        help_text=_("Maximum required professional experience in years."),
    )
    education_level = models.CharField(
        max_length=30,
        choices=EducationLevel.choices,
        default=EducationLevel.BACHELOR,
        db_index=True,
    )
    salary_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Starting or minimum compensation figure."),
    )
    salary_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Ceiling or maximum compensation figure."),
    )
    currency = models.CharField(
        max_length=5,
        choices=CURRENCY_CHOICES,
        default=DEFAULT_CURRENCY,
    )
    is_salary_negotiable = models.BooleanField(
        default=False,
        help_text=_("Check if salary can be negotiated based on candidate caliber."),
    )
    location = models.CharField(
        max_length=200,
        db_index=True,
        help_text=_("City, State, Country or 'Remote'."),
    )
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.ACTIVE,
        db_index=True,
    )
    deadline = models.DateTimeField(
        validators=[validate_future_deadline],
        help_text=_("Closing timestamp for receiving candidate applications."),
    )
    views_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Total views accrued on this job page."),
    )
    applications_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Cached tally of candidates who applied for this role."),
    )
    skills = models.ManyToManyField(
        Skill,
        through="JobRequiredSkill",
        related_name="jobs",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Job")
        verbose_name_plural = _("Jobs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "deadline"]),
            models.Index(fields=["recruiter", "status"]),
            models.Index(fields=["job_type", "workplace_type"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.location}")
            candidate_slug = base_slug
            counter = 1
            while Job.objects.filter(slug=candidate_slug).exclude(pk=self.pk).exists():
                candidate_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} @ {self.recruiter.get_full_name() or self.recruiter.username} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"slug": self.slug})

    @property
    def is_active(self) -> bool:
        """Determines if the job is active and has not expired."""
        return self.status == JobStatus.ACTIVE and self.deadline > timezone.now()

    @property
    def days_remaining(self) -> int:
        """Calculates days until application deadline expires."""
        delta = self.deadline - timezone.now()
        return max(0, delta.days)


class JobRequiredSkill(models.Model):
    """Many-to-Many intermediate model connecting Jobs with required Skills and weights."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_required_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="job_requirements")
    is_mandatory = models.BooleanField(
        default=True,
        help_text=_("Must-have core skill required to pass ATS screening thresholds."),
    )
    min_years_experience = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        help_text=_("Minimum years of experience required specifically with this skill."),
    )

    class Meta:
        verbose_name = _("Job Required Skill")
        verbose_name_plural = _("Job Required Skills")
        unique_together = ("job", "skill")

    def __str__(self):
        flag = "Mandatory" if self.is_mandatory else "Preferred"
        return f"{self.skill.name} ({flag}) for {self.job.title}"

