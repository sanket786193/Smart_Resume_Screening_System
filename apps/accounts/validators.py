"""
Validators for User accounts and profile uploads.
"""
from django.core.exceptions import ValidationError
from PIL import Image
from .constants import MAX_AVATAR_SIZE_BYTES, ALLOWED_AVATAR_EXTENSIONS


def validate_profile_photo(photo_file):
    """
    Validates uploaded profile image:
    1. Size limit (max 5 MB)
    2. File format (JPEG, PNG, WEBP)
    3. Structural image integrity via Pillow
    """
    if not photo_file:
        return

    if photo_file.size > MAX_AVATAR_SIZE_BYTES:
        raise ValidationError(
            f"Image file size cannot exceed 5MB. Uploaded size: {photo_file.size / (1024*1024):.2f}MB."
        )

    name_lower = photo_file.name.lower()
    if not any(name_lower.endswith(ext) for ext in ALLOWED_AVATAR_EXTENSIONS):
        raise ValidationError("Unsupported image format. Allowed formats: JPG, PNG, WEBP.")

    try:
        photo_file.seek(0)
        img = Image.open(photo_file)
        img.verify()
        photo_file.seek(0)
    except Exception as exc:
        raise ValidationError("Uploaded file is corrupted or not a valid image.") from exc

