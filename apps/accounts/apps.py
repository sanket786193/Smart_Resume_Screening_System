"""Accounts application configuration."""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "User Authentication & Accounts"

    def ready(self):
        # Import signal handlers if needed in future extensions
        pass

