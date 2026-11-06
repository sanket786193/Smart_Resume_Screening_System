"""Job Description Parser for extracting requirements, skills, experience, and education."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from ai.skill_extractor import skill_extractor
from ai.utils import deduplicate_preserve_order


class JobDescriptionParser:
    """Extracts structured requirements from job descriptions and Job model instances."""

    def __init__(self) -> None:
        self.exp_pattern = re.compile(
            r"(?:(\d+)(?:\s*(?:-|to)\s*(\d+))?|\b(\d+)\+?)\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)",
            re.IGNORECASE,
        )
        self.edu_patterns = {
            "Doctorate": re.compile(r"\b(ph\.?d|doctorate)\b", re.IGNORECASE),
            "Master's": re.compile(r"\b(master'?s|m\.?s|m\.?tech|m\.?sc|mba)\b", re.IGNORECASE),
            "Bachelor's": re.compile(r"\b(bachelor'?s|b\.?s|b\.?tech|b\.?e|b\.?sc|undergraduate|degree)\b", re.IGNORECASE),
            "Diploma": re.compile(r"\b(diploma|associate)\b", re.IGNORECASE),
        }

    def extract_experience_requirement(self, text: str) -> tuple[int, Optional[int]]:
        """Extract min and max years of experience from text. Returns (min_years, max_years)."""
        matches = self.exp_pattern.findall(text)
        if not matches:
            return 0, None
        
        for m in matches:
            low, high, single = m
            if low and high:
                return int(low), int(high)
            if low:
                return int(low), None
            if single:
                return int(single), None
        return 0, None

    def extract_education_requirement(self, text: str) -> str:
        """Identify required education tier."""
        for level, pattern in self.edu_patterns.items():
            if pattern.search(text):
                return level
        return "Any Degree"

    def parse_job(self, job_obj: Any) -> Dict[str, Any]:
        """Extract all structured requirements from a Job model instance or dictionary."""
        title = getattr(job_obj, "title", "")
        description = getattr(job_obj, "description", "") or ""
        requirements = getattr(job_obj, "requirements", "") or ""
        responsibilities = getattr(job_obj, "responsibilities", "") or ""

        min_exp = getattr(job_obj, "experience_min", getattr(job_obj, "minimum_experience", 0))
        max_exp = getattr(job_obj, "experience_max", getattr(job_obj, "maximum_experience", None))
        edu = getattr(job_obj, "education_level", getattr(job_obj, "education", "")) or ""

        # Extract explicit skills from Job model relationships
        explicit_required: List[str] = []
        explicit_preferred: List[str] = []

        if hasattr(job_obj, "job_required_skills"):
            for jrs in job_obj.job_required_skills.select_related("skill").all():
                if jrs.is_mandatory:
                    explicit_required.append(jrs.skill.name)
                else:
                    explicit_preferred.append(jrs.skill.name)
        elif hasattr(job_obj, "skills"):
            for s in job_obj.skills.all():
                explicit_required.append(s.name)

        # In case job_obj had string fields like required_skills / preferred_skills
        raw_req_str = getattr(job_obj, "required_skills", "") or ""
        raw_pref_str = getattr(job_obj, "preferred_skills", "") or ""
        if raw_req_str:
            explicit_required.extend([s.strip() for s in raw_req_str.split(",") if s.strip()])
        if raw_pref_str:
            explicit_preferred.extend([s.strip() for s in raw_pref_str.split(",") if s.strip()])

        full_text = f"{title}\n{description}\n{requirements}\n{responsibilities}\n{' '.join(explicit_required)}\n{' '.join(explicit_preferred)}"
        extracted_skills = skill_extractor.extract_skills_from_text(full_text)

        all_required = deduplicate_preserve_order(explicit_required + extracted_skills)
        all_preferred = deduplicate_preserve_order(explicit_preferred)

        if not min_exp:
            text_min, text_max = self.extract_experience_requirement(full_text)
            min_exp = text_min
            if not max_exp:
                max_exp = text_max

        if not edu or edu in ("Any", "OTHER"):
            edu = self.extract_education_requirement(full_text)

        return {
            "title": title,
            "min_experience": min_exp or 0,
            "max_experience": max_exp,
            "required_education": edu or "Bachelor's",
            "required_skills": all_required,
            "preferred_skills": all_preferred,
            "full_text": full_text,
        }


# Singleton instance
jd_parser = JobDescriptionParser()
