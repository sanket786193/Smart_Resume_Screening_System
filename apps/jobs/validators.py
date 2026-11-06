"""
Validation rules for Job postings, salaries, and application deadlines.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone
from .constants import MAX_EXPERIENCE_YEARS


def validate_future_deadline(value):
    """Ensures the application deadline is set to a future timestamp."""
    if value and value <= timezone.now():
        raise ValidationError("Application deadline must be a future date and time.")


def validate_salary_range(min_salary, max_salary):
    """Ensures minimum salary does not exceed maximum salary."""
    if min_salary is not None and max_salary is not None:
        if min_salary < 0 or max_salary < 0:
            raise ValidationError("Salary figures cannot be negative.")
        if min_salary > max_salary:
            raise ValidationError("Minimum salary cannot exceed maximum salary.")


def validate_experience_range(min_exp, max_exp):
    """Validates sensible bounds for required years of experience."""
    if min_exp is not None and min_exp < 0:
        raise ValidationError("Minimum experience cannot be negative.")
    if max_exp is not None and max_exp > MAX_EXPERIENCE_YEARS:
        raise ValidationError(f"Maximum experience cannot exceed {MAX_EXPERIENCE_YEARS} years.")
    if min_exp is not None and max_exp is not None and min_exp > max_exp:
        raise ValidationError("Minimum experience cannot be greater than maximum experience.")

