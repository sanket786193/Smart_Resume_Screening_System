"""
Constants and Configuration for the Resumes application.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_RESUME_EXTENSIONS = (".pdf", ".docx")

ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
)


class ParsingStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Analysis")
    SUCCESS = "SUCCESS", _("Parsed Successfully")
    OCR_PROCESSED = "OCR_PROCESSED", _("Parsed via OCR Fallback")
    FAILED = "FAILED", _("Parsing Failed")


class ResumeFormat(models.TextChoices):
    PDF = "PDF", _("Portable Document Format (.pdf)")
    DOCX = "DOCX", _("Microsoft Word (.docx)")

