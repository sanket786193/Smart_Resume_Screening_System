"""Resumes app configuration."""
from django.apps import AppConfig


class ResumesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "resumes"
    verbose_name = "Resume Intelligence & Documents"

    def ready(self):
        import resumes.signals  # noqa: F401
