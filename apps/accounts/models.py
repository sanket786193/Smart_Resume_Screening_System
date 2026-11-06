"""
Models for the Accounts application.
Includes Custom User with Role-Based Access Control, Profiles, and Audit Logs.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager for the User model supporting email-based lookups and role assignment."""

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        if not username:
            raise ValueError(_("The Username field must be set"))

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Primary custom user model supporting 3 core system roles:
    - Candidate
    - Recruiter
    - Admin
    """

    class Role(models.TextChoices):
        CANDIDATE = "CANDIDATE", _("Candidate")
        RECRUITER = "RECRUITER", _("Recruiter")
        ADMIN = "ADMIN", _("Admin")

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CANDIDATE,
        db_index=True,
        help_text=_("Designates the user's operational role in the ATS platform."),
    )
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."),
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        help_text=_("Contact phone number in international format."),
    )
    profile_photo = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Optional profile photo. Maximum size 5MB."),
    )
    bio = models.TextField(
        blank=True,
        null=True,
        max_length=1000,
        help_text=_("Brief bio or professional summary."),
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether this user has verified their email address."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "role"]),
            models.Index(fields=["username", "role"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_candidate(self) -> bool:
        return self.role == self.Role.CANDIDATE

    @property
    def is_recruiter(self) -> bool:
        return self.role == self.Role.RECRUITER

    @property
    def is_admin_user(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser


class CandidateProfile(models.Model):
    """Candidate-specific extended details and portfolio references."""

    EDUCATION_CHOICES = [
        ("HIGH_SCHOOL", _("High School")),
        ("ASSOCIATE", _("Associate Degree")),
        ("BACHELOR", _("Bachelor's Degree")),
        ("MASTER", _("Master's Degree")),
        ("DOCTORATE", _("Doctorate (PhD)")),
        ("OTHER", _("Other / Self-Taught")),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
        limit_choices_to={"role": User.Role.CANDIDATE},
    )
    current_job_title = models.CharField(max_length=150, blank=True, null=True)
    experience_years = models.DecimalField(
        max_length=4,
        max_digits=4,
        decimal_places=1,
        default=0.0,
        help_text=_("Total years of professional experience."),
    )
    education_level = models.CharField(
        max_length=30,
        choices=EDUCATION_CHOICES,
        default="BACHELOR",
    )
    linkedin_url = models.URLField(max_length=300, blank=True, null=True)
    github_url = models.URLField(max_length=300, blank=True, null=True)
    portfolio_url = models.URLField(max_length=300, blank=True, null=True)
    expected_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Candidate's expected annual compensation."),
    )
    preferred_location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Preferred work location (e.g., Remote, New York, London)."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Candidate Profile")
        verbose_name_plural = _("Candidate Profiles")

    def __str__(self):
        return f"Candidate: {self.user.get_full_name() or self.user.username}"


class RecruiterProfile(models.Model):
    """Recruiter-specific enterprise employer details."""

    COMPANY_SIZE_CHOICES = [
        ("1-10", _("1-10 employees (Startup)")),
        ("11-50", _("11-50 employees (Small)")),
        ("51-200", _("51-200 employees (Mid-sized)")),
        ("201-1000", _("201-1000 employees (Large)")),
        ("1000+", _("1000+ employees (Enterprise)")),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"role": User.Role.RECRUITER},
    )
    company_name = models.CharField(max_length=200, help_text=_("Name of the hiring organization."))
    company_website = models.URLField(max_length=300, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True, help_text=_("e.g. Lead Talent Acquisition Partner"))
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES, default="51-200")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Recruiter Profile")
        verbose_name_plural = _("Recruiter Profiles")

    def __str__(self):
        return f"Recruiter: {self.user.username} @ {self.company_name}"


class AuditLog(models.Model):
    """Comprehensive compliance and security audit trail for user operations."""

    class Action(models.TextChoices):
        LOGIN_SUCCESS = "LOGIN_SUCCESS", _("Login Success")
        LOGIN_FAILURE = "LOGIN_FAILURE", _("Login Failure")
        LOGOUT = "LOGOUT", _("Logout")
        REGISTER = "REGISTER", _("User Registered")
        PASSWORD_CHANGE = "PASSWORD_CHANGE", _("Password Changed")
        PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST", _("Password Reset Requested")
        PASSWORD_RESET_COMPLETE = "PASSWORD_RESET_COMPLETE", _("Password Reset Completed")
        PROFILE_UPDATE = "PROFILE_UPDATE", _("Profile Updated")
        ACCOUNT_ACTIVATED = "ACCOUNT_ACTIVATED", _("Account Activated")
        ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED", _("Account Deactivated")
        ROLE_CHANGED = "ROLE_CHANGED", _("Role Changed")

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text=_("User associated with the event; null if action was by anonymous/deleted user."),
    )
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    details = models.JSONField(default=dict, blank=True, help_text=_("Contextual event metadata."))
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.action} by {username}"

