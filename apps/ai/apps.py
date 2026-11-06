"""AI application configuration."""
from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"
    verbose_name = "AI Resume Screening & Ranking Engine"
