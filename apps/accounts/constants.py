"""
Constants for the Accounts application.
"""
from django.db import models


MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_AVATAR_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

DEFAULT_SESSION_AGE = 86400 * 7  # 7 days
PASSWORD_RESET_TIMEOUT_DAYS = 1

ROLE_CANDIDATE = "CANDIDATE"
ROLE_RECRUITER = "RECRUITER"
ROLE_ADMIN = "ADMIN"


class Role(models.TextChoices):
    CANDIDATE = "CANDIDATE", "Candidate"
    RECRUITER = "RECRUITER", "Recruiter"
    ADMIN = "ADMIN", "Admin"
