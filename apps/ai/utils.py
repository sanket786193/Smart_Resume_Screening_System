"""AI Module utilities and text helpers."""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any, List, Set


def normalize_text(text: str | None) -> str:
    """Normalize text by converting unicode, lowercasing, and stripping whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def clean_tokens(tokens: List[str]) -> List[str]:
    """Filter out empty and non-alphanumeric tokens while preserving common tech terms."""
    cleaned = []
    for token in tokens:
        t = token.strip().lower()
        if t and (t.isalnum() or t in {"c++", "c#", ".net", "node.js", "vue.js", "react.js"}):
            cleaned.append(t)
    return cleaned


def clamp_score(score: float | int | Decimal, min_val: float = 0.0, max_val: float = 100.0) -> Decimal:
    """Clamp a numerical score between min_val and max_val and return as Decimal."""
    val = float(score)
    val = max(min_val, min(max_val, val))
    return Decimal(f"{val:.2f}")


def deduplicate_preserve_order(items: List[str]) -> List[str]:
    """Remove case-insensitive duplicates while preserving original case and order."""
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
