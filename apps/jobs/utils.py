"""
Utility helpers for Jobs parsing, skill normalization, and display formatting.
"""
from typing import List
from django.utils.text import slugify
from .models import Skill, Job, JobRequiredSkill


def parse_skills_string(skills_str: str) -> List[str]:
    """
    Cleans and deduplicates a comma-delimited string of skills.
    Example: "Python, Django, python, React.js " -> ["Python", "Django", "React.js"]
    """
    if not skills_str:
        return []

    tokens = [part.strip() for part in skills_str.split(",") if part.strip()]
    seen = set()
    cleaned = []
    for token in tokens:
        lower = token.lower()
        if lower not in seen:
            seen.add(lower)
            cleaned.append(token)
    return cleaned


def sync_job_skills(job: Job, skills_list: List[str]) -> None:
    """
    Atomically ensures each skill exists in the normalized Skill repository
    and connects it to the Job through JobRequiredSkill.
    Removes disconnected skills if they are removed in an edit.
    """
    current_skill_pks = []

    for name in skills_list:
        slug = slugify(name)
        skill, _ = Skill.objects.get_or_create(
            slug=slug,
            defaults={"name": name.strip(), "category": "OTHER"},
        )
        JobRequiredSkill.objects.get_or_create(
            job=job,
            skill=skill,
            defaults={"is_mandatory": True, "min_years_experience": job.experience_min},
        )
        current_skill_pks.append(skill.pk)

    # Clean up obsolete skills that were unassigned in edit form
    JobRequiredSkill.objects.filter(job=job).exclude(skill__pk__in=current_skill_pks).delete()


def format_salary_display(job: Job) -> str:
    """Formats salary range into a clean string representation."""
    if not job.salary_min and not job.salary_max:
        return "Competitive / Negotiable" if job.is_salary_negotiable else "Not Disclosed"

    curr = job.currency or "USD"
    if job.salary_min and job.salary_max:
        return f"{curr} {job.salary_min:,.0f} - {job.salary_max:,.0f}"
    elif job.salary_min:
        return f"From {curr} {job.salary_min:,.0f}"
    else:
        return f"Up to {curr} {job.salary_max:,.0f}"


def get_skills_as_comma_separated(job: Job) -> str:
    """Serializes a job's assigned skills into a comma-separated string for editing."""
    return ", ".join(job.skills.values_list("name", flat=True))

