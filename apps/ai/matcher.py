"""Resume and Job Matching engine utilizing TF-IDF, Cosine Similarity, and RapidFuzz."""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ai.preprocess import preprocessor
from ai.skill_extractor import skill_extractor
from ai.utils import clamp_score, deduplicate_preserve_order


class ResumeJobMatcher:
    """Matches resumes against job requirements using vector space and token similarity."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )

    def calculate_cosine_similarity(self, resume_text: str, jd_text: str) -> float:
        """Compute TF-IDF cosine similarity percentage between resume and job description."""
        clean_resume = preprocessor.preprocess(resume_text)
        clean_jd = preprocessor.preprocess(jd_text)

        if not clean_resume or not clean_jd:
            return 0.0

        try:
            tfidf_matrix = self.vectorizer.fit_transform([clean_resume, clean_jd])
            similarity_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            score = float(similarity_matrix[0][0]) * 100.0
            return float(clamp_score(score, 0.0, 100.0))
        except Exception:
            return 0.0

    def match_skills(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        preferred_skills: List[str] | None = None,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identify matching skills, missing required skills, and suggested preferred skills."""
        preferred_skills = preferred_skills or []
        matched: List[str] = []
        missing: List[str] = []
        suggested: List[str] = []

        for req in required_skills:
            if skill_extractor.match_skill_fuzzy(req, candidate_skills, threshold=80.0):
                matched.append(req)
            else:
                missing.append(req)

        for pref in preferred_skills:
            if skill_extractor.match_skill_fuzzy(pref, candidate_skills, threshold=80.0):
                if pref not in matched:
                    matched.append(pref)
            else:
                if pref not in missing:
                    suggested.append(pref)

        return (
            deduplicate_preserve_order(matched),
            deduplicate_preserve_order(missing),
            deduplicate_preserve_order(suggested),
        )

    def compute_match(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute complete matching profile including cosine similarity and skill breakdown."""
        resume_text = resume_data.get("raw_text", "")
        jd_text = job_data.get("full_text", "")

        candidate_skills = resume_data.get("skills", [])
        required_skills = job_data.get("required_skills", [])
        preferred_skills = job_data.get("preferred_skills", [])

        cosine_pct = self.calculate_cosine_similarity(resume_text, jd_text)

        matched_skills, missing_skills, suggested_skills = self.match_skills(
            candidate_skills, required_skills, preferred_skills
        )

        total_req = len(required_skills)
        skill_coverage_ratio = (len(matched_skills) / total_req) if total_req > 0 else 1.0
        skill_match_pct = float(clamp_score(skill_coverage_ratio * 100.0, 0.0, 100.0))

        blended_match_pct = (skill_match_pct * 0.60) + (cosine_pct * 0.40)

        return {
            "match_percentage": float(clamp_score(blended_match_pct)),
            "cosine_similarity": cosine_pct,
            "skill_match_percentage": skill_match_pct,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "suggested_skills": suggested_skills,
        }


# Singleton instance
resume_matcher = ResumeJobMatcher()
