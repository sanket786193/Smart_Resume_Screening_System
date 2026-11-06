"""Constants for the AI screening, scoring, and recommendation engine."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict

# Multi-criteria scoring weights (Sum = 1.00)
WEIGHT_SKILLS: float = 0.40
WEIGHT_EXPERIENCE: float = 0.25
WEIGHT_EDUCATION: float = 0.15
WEIGHT_PROJECTS: float = 0.10
WEIGHT_CERTIFICATIONS: float = 0.10

ATS_SCORING_WEIGHTS: Dict[str, float] = {
    "skills": WEIGHT_SKILLS,
    "experience": WEIGHT_EXPERIENCE,
    "education": WEIGHT_EDUCATION,
    "projects": WEIGHT_PROJECTS,
    "certifications": WEIGHT_CERTIFICATIONS,
}

# Score Tier Thresholds
TIER_HIGH_THRESHOLD: float = 80.0
TIER_MEDIUM_THRESHOLD: float = 60.0

TIER_STRONG_LABEL: str = "Strong Match"
TIER_MODERATE_LABEL: str = "Moderate Match"
TIER_LOW_LABEL: str = "Low Match"

# RapidFuzz / TF-IDF Matching Configuration
FUZZY_MATCH_THRESHOLD: float = 75.0
TFIDF_MAX_FEATURES: int = 5000
TFIDF_NGRAM_RANGE: tuple[int, int] = (1, 2)

# Semantic vs Skill Blend Ratio
SKILL_COVERAGE_WEIGHT: float = 0.60
SEMANTIC_TFIDF_WEIGHT: float = 0.40

# Minimum and Maximum Score Bounds
SCORE_MIN: Decimal = Decimal("0.00")
SCORE_MAX: Decimal = Decimal("100.00")

# Educational Hierarchy Ranking
EDUCATION_RANKING_MAP: Dict[str, int] = {
    "Doctorate": 4,
    "Master's": 3,
    "Bachelor's": 2,
    "Diploma": 1,
    "Any Degree": 1,
    "OTHER": 1,
}

