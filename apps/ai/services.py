"""Business logic service layer for AI screening, matching, ranking, and scoring."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.db import transaction

from ai.ats_score import ats_scorer
from ai.jd_parser import jd_parser
from ai.matcher import resume_matcher
from ai.models import ATSAnalysisResult
from ai.ranking import candidate_ranker
from ai.recommendation import recommendation_engine
from ai.resume_parser import ai_resume_parser

logger = logging.getLogger(__name__)


class AIService:
    """Service facade coordinating resume parsing, job matching, ATS scoring, and candidate ranking."""

    @staticmethod
    def parse_resume_content(raw_text: str) -> Dict[str, Any]:
        """Parse raw resume text into structured candidate dictionary."""
        return ai_resume_parser.parse_text(raw_text)

    @classmethod
    def analyze_resume_against_job(
        cls,
        resume: Any,
        job: Any,
        save: bool = True,
    ) -> ATSAnalysisResult:
        """Execute full AI screening pipeline between a Resume instance and a Job instance."""
        resume_data = ai_resume_parser.parse_resume_instance(resume)
        job_data = jd_parser.parse_job(job)

        match_data = resume_matcher.compute_match(resume_data, job_data)
        ats_score_data = ats_scorer.calculate_score(resume_data, job_data, match_data)
        recommendations = recommendation_engine.generate_recommendations(
            resume_data, job_data, match_data, ats_score_data
        )

        matched_str = ", ".join(match_data.get("matched_skills", [])) or "None identified"
        missing_str = ", ".join(match_data.get("missing_skills", [])) or "None"
        overall = ats_score_data.get("overall_score", 0.0)
        summary = (
            f"Candidate scored {overall}% overall ATS suitability for '{job.title}'. "
            f"Matched competencies: {matched_str}. Key skill gaps: {missing_str}."
        )

        if not save:
            return ATSAnalysisResult(
                resume=resume,
                job=job,
                overall_score=Decimal(str(ats_score_data["overall_score"])),
                match_percentage=Decimal(str(match_data["match_percentage"])),
                skills_score=Decimal(str(ats_score_data["skills_score"])),
                experience_score=Decimal(str(ats_score_data["experience_score"])),
                education_score=Decimal(str(ats_score_data["education_score"])),
                projects_score=Decimal(str(ats_score_data["projects_score"])),
                certifications_score=Decimal(str(ats_score_data["certifications_score"])),
                matched_skills=match_data["matched_skills"],
                missing_skills=match_data["missing_skills"],
                suggested_skills=match_data["suggested_skills"],
                recommendations=recommendations,
                summary=summary,
            )

        with transaction.atomic():
            result, _ = ATSAnalysisResult.objects.update_or_create(
                resume=resume,
                job=job,
                defaults={
                    "overall_score": Decimal(str(ats_score_data["overall_score"])),
                    "match_percentage": Decimal(str(match_data["match_percentage"])),
                    "skills_score": Decimal(str(ats_score_data["skills_score"])),
                    "experience_score": Decimal(str(ats_score_data["experience_score"])),
                    "education_score": Decimal(str(ats_score_data["education_score"])),
                    "projects_score": Decimal(str(ats_score_data["projects_score"])),
                    "certifications_score": Decimal(str(ats_score_data["certifications_score"])),
                    "matched_skills": match_data["matched_skills"],
                    "missing_skills": match_data["missing_skills"],
                    "suggested_skills": match_data["suggested_skills"],
                    "recommendations": recommendations,
                    "summary": summary,
                },
            )

        return result

    @classmethod
    def rank_candidates_for_job(cls, job: Any, resumes: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Rank candidates who submitted resumes for a given job."""
        if resumes is None:
            evaluations = ATSAnalysisResult.objects.filter(job=job).select_related(
                "resume", "resume__candidate"
            )
        else:
            evaluations = []
            for res in resumes:
                evaluation = cls.analyze_resume_against_job(res, job, save=True)
                evaluations.append(evaluation)

        candidates_data = []
        for ev in evaluations:
            cand_user = getattr(ev.resume, "candidate", getattr(ev.resume, "user", None))
            cand_name = cand_user.get_full_name() if cand_user else "Candidate"
            cand_email = cand_user.email if cand_user else ""
            years = len(getattr(ev.resume, "extracted_experience", [])) * 2 or 3

            candidates_data.append({
                "resume_id": ev.resume.id,
                "candidate_name": cand_name or (cand_user.username if cand_user else "Candidate"),
                "candidate_email": cand_email,
                "overall_score": float(ev.overall_score),
                "match_percentage": float(ev.match_percentage),
                "skills_score": float(ev.skills_score),
                "experience_years": years,
                "matched_skills": ev.matched_skills,
                "missing_skills": ev.missing_skills,
                "evaluation_id": ev.id,
            })

        return candidate_ranker.rank_candidates(candidates_data)

    @classmethod
    def batch_screen_job_resumes(cls, job: Any) -> int:
        """Run AI screening across all candidate resumes in the system for a given job."""
        from resumes.models import Resume

        resumes = Resume.objects.filter(is_primary=True)
        count = 0
        for res in resumes:
            cls.analyze_resume_against_job(res, job, save=True)
            count += 1
        return count
