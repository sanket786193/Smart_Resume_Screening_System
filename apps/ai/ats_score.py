"""ATS Scoring Engine calculating normalized 0-100 scores across weighted criteria."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict
from ai.constants import ATS_SCORING_WEIGHTS, EDUCATION_RANKING_MAP
from ai.utils import clamp_score


class ATSScorer:
    """Calculates weighted ATS compatibility score (0-100) using 5 dimensional criteria."""

    WEIGHTS = ATS_SCORING_WEIGHTS
    EDUCATION_HIERARCHY = EDUCATION_RANKING_MAP

    def score_skills(self, matched_count: int, total_required: int) -> float:
        """Score skills match (0 - 100)."""
        if total_required <= 0:
            return 100.0 if matched_count > 0 else 70.0
        ratio = min(1.0, matched_count / total_required)
        return float(clamp_score(ratio * 100.0))

    def score_experience(self, candidate_years: int, required_min: int) -> float:
        """Score experience based on candidate years vs requirement (0 - 100)."""
        if required_min <= 0:
            return 100.0 if candidate_years > 0 else 85.0
        
        if candidate_years >= required_min:
            surplus = min(5, candidate_years - required_min)
            return float(clamp_score(90.0 + (surplus * 2.0)))
        
        ratio = max(0.0, candidate_years / required_min)
        return float(clamp_score(ratio * 80.0))

    def score_education(self, candidate_education: list[str], required_education: str) -> float:
        """Score education hierarchy alignment (0 - 100)."""
        if not required_education or required_education in ("Any Degree", "Any"):
            return 100.0 if candidate_education else 80.0

        target_tier = self.EDUCATION_HIERARCHY.get(required_education, 2)
        highest_cand_tier = 0

        for edu_str in candidate_education:
            edu_lower = edu_str.lower()
            if any(term in edu_lower for term in ["phd", "doctorate"]):
                highest_cand_tier = max(highest_cand_tier, 4)
            elif any(term in edu_lower for term in ["master", "m.s.", "m.tech", "mba"]):
                highest_cand_tier = max(highest_cand_tier, 3)
            elif any(term in edu_lower for term in ["bachelor", "b.s.", "b.tech", "b.e."]):
                highest_cand_tier = max(highest_cand_tier, 2)
            else:
                highest_cand_tier = max(highest_cand_tier, 1)

        if highest_cand_tier >= target_tier:
            return 100.0
        elif highest_cand_tier == target_tier - 1:
            return 75.0
        elif highest_cand_tier > 0:
            return 50.0
        return 30.0

    def score_projects(self, projects: list[str]) -> float:
        """Score practical demonstrated projects (0 - 100)."""
        count = len(projects)
        if count >= 3:
            return 100.0
        if count == 2:
            return 80.0
        if count == 1:
            return 60.0
        return 20.0

    def score_certifications(self, certs: list[str]) -> float:
        """Score industry certifications (0 - 100)."""
        count = len(certs)
        if count >= 2:
            return 100.0
        if count == 1:
            return 75.0
        return 25.0

    def calculate_score(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        match_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute holistic ATS score and sub-scores."""
        matched_skills = match_data.get("matched_skills", [])
        required_skills = job_data.get("required_skills", [])

        skills_score = self.score_skills(len(matched_skills), len(required_skills))
        exp_score = self.score_experience(
            resume_data.get("experience_years", 0),
            job_data.get("min_experience", 0),
        )
        edu_score = self.score_education(
            resume_data.get("education", []),
            job_data.get("required_education", "Bachelor's"),
        )
        proj_score = self.score_projects(resume_data.get("projects", []))
        cert_score = self.score_certifications(resume_data.get("certifications", []))

        overall = (
            (skills_score * self.WEIGHTS["skills"])
            + (exp_score * self.WEIGHTS["experience"])
            + (edu_score * self.WEIGHTS["education"])
            + (proj_score * self.WEIGHTS["projects"])
            + (cert_score * self.WEIGHTS["certifications"])
        )

        overall_clamped = clamp_score(overall, 0.0, 100.0)

        return {
            "overall_score": float(overall_clamped),
            "skills_score": skills_score,
            "experience_score": exp_score,
            "education_score": edu_score,
            "projects_score": proj_score,
            "certifications_score": cert_score,
        }


# Singleton instance
ats_scorer = ATSScorer()
