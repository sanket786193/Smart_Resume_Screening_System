"""
File validators for Resume uploads ensuring strict format and size boundaries.
"""
import os
from django.core.exceptions import ValidationError
from .constants import MAX_RESUME_SIZE_BYTES, ALLOWED_RESUME_EXTENSIONS


def validate_resume_file(uploaded_file):
    """
    Validates uploaded resume file:
    1. Maximum size limit (10 MB).
    2. Explicit extension check (.pdf, .docx only).
    3. Non-empty file stream.
    """
    if not uploaded_file:
        raise ValidationError("No file was uploaded.")

    # Size validation
    if uploaded_file.size > MAX_RESUME_SIZE_BYTES:
        size_mb = uploaded_file.size / (1024 * 1024)
        raise ValidationError(
            f"File size exceeds the 10 MB limit. Uploaded file is {size_mb:.2f} MB."
        )

    if uploaded_file.size == 0:
        raise ValidationError("Uploaded file is empty (0 bytes).")

    # Extension validation
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        allowed = ", ".join(ALLOWED_RESUME_EXTENSIONS)
        raise ValidationError(
            f"Unsupported file format '{ext}'. Allowed formats: {allowed}."
        )

