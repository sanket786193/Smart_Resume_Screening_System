"""Validators for the AI screening and scoring application."""
from __future__ import annotations

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ai.constants import SCORE_MAX, SCORE_MIN


def validate_score_range(value: Decimal | float | int) -> None:
    """Validate that score remains bounded between 0.00 and 100.00."""
    dec_val = Decimal(str(value))
    if dec_val < SCORE_MIN or dec_val > SCORE_MAX:
        raise ValidationError(
            _("Score %(value)s is out of range. Must be between 0.00 and 100.00."),
            params={"value": value},
        )


def validate_skill_list(skills: list[str]) -> None:
    """Validate that input skills list contains non-empty strings."""
    if not isinstance(skills, (list, tuple, set)):
        raise ValidationError(_("Skills must be provided as a list or collection."))
    for item in skills:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(_("Each skill must be a non-empty string."))


def validate_raw_corpus(text: str) -> None:
    """Validate that raw textual corpus is non-empty before running NLP pipelines."""
    if not text or not text.strip():
        raise ValidationError(_("Text corpus cannot be empty for AI evaluation."))

