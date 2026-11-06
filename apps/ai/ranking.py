"""Candidate Ranking and Leaderboard engine for recruiter shortlisting."""
from __future__ import annotations

from typing import Any, Dict, List


class CandidateRanker:
    """Ranks multiple candidates for a job based on ATS Score, Experience, Skills, and Education."""

    @staticmethod
    def rank_candidates(candidates_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort and rank a list of candidate evaluation dictionaries.
        
        Sorting hierarchy:
            1. overall_score (descending)
            2. skills_score (descending)
            3. experience_years (descending)
            4. cosine_similarity (descending)
        """
        if not candidates_data:
            return []

        # Sort with strict multi-key tie breaking
        ranked = sorted(
            candidates_data,
            key=lambda c: (
                float(c.get("overall_score", 0)),
                float(c.get("skills_score", 0)),
                int(c.get("experience_years", 0)),
                float(c.get("match_percentage", 0)),
            ),
            reverse=True,
        )

        total_count = len(ranked)
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index
            score = float(item.get("overall_score", 0))
            
            # Tier categorization
            if score >= 80.0:
                item["tier"] = "Tier 1: High Fit"
                item["recommended_action"] = "Schedule Interview Immediately"
            elif score >= 60.0:
                item["tier"] = "Tier 2: Medium Fit"
                item["recommended_action"] = "Review Resume Manually"
            else:
                item["tier"] = "Tier 3: Low Fit"
                item["recommended_action"] = "Consider for Alternate Openings"

            # Percentile rank
            percentile = ((total_count - index + 1) / total_count) * 100.0 if total_count > 0 else 100.0
            item["percentile"] = round(percentile, 1)

        return ranked


# Singleton instance
candidate_ranker = CandidateRanker()

