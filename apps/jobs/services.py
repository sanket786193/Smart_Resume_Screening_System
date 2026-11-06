"""
Service Layer for Job Postings, Skill Linkages, Search & Filtering, and Lifecycle Operations.
Implements the Service/Repository pattern adhering strictly to SOLID principles.
"""
import logging
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.db.models import Q, F, QuerySet
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from .models import Job, Skill, JobRequiredSkill
from .constants import JobStatus
from .utils import parse_skills_string, sync_job_skills

logger = logging.getLogger(__name__)


class JobService:
    """Encapsulates all transactional business operations regarding Job Postings."""

    @staticmethod
    @transaction.atomic
    def create_job(recruiter, job_data: Dict[str, Any], skills_str: str) -> Job:
        """
        Creates a new Job listing attached to the authenticated recruiter.
        Normalizes and links required skills atomically.
        """
        if not getattr(recruiter, "is_recruiter", False) and not recruiter.is_superuser:
            raise PermissionDenied("Only verified Recruiters can post new job openings.")

        skills_list = parse_skills_string(skills_str)
        if not skills_list:
            raise ValidationError("A job opening must require at least one skill.")

        job = Job.objects.create(recruiter=recruiter, **job_data)
        sync_job_skills(job, skills_list)

        logger.info(f"Job created: '{job.title}' (ID: {job.pk}) by {recruiter.username}")
        return job

    @staticmethod
    @transaction.atomic
    def update_job(job: Job, job_data: Dict[str, Any], skills_str: str, user) -> Job:
        """
        Updates an existing Job listing and refreshes its associated skills.
        Guarantees that only the authoring recruiter or an admin can modify it.
        """
        JobService._check_job_ownership(job, user)

        skills_list = parse_skills_string(skills_str)
        if not skills_list:
            raise ValidationError("A job opening must require at least one skill.")

        for field, value in job_data.items():
            setattr(job, field, value)

        job.save()
        sync_job_skills(job, skills_list)

        logger.info(f"Job updated: '{job.title}' (ID: {job.pk}) by {user.username}")
        return job

    @staticmethod
    def close_job(job: Job, user) -> Job:
        """Closes a job posting so no further applications are accepted."""
        JobService._check_job_ownership(job, user)
        job.status = JobStatus.CLOSED
        job.save(update_fields=["status", "updated_at"])
        logger.info(f"Job closed: '{job.title}' (ID: {job.pk}) by {user.username}")
        return job

    @staticmethod
    def reopen_job(job: Job, user, new_deadline=None) -> Job:
        """Re-activates a previously closed or draft job."""
        JobService._check_job_ownership(job, user)
        if new_deadline:
            if new_deadline <= timezone.now():
                raise ValidationError("New deadline must be in the future.")
            job.deadline = new_deadline
        elif job.deadline <= timezone.now():
            raise ValidationError("Cannot reopen job with an expired deadline. Please set a future deadline.")

        job.status = JobStatus.ACTIVE
        job.save(update_fields=["status", "deadline", "updated_at"])
        logger.info(f"Job reopened: '{job.title}' (ID: {job.pk}) by {user.username}")
        return job

    @staticmethod
    def delete_job(job: Job, user) -> None:
        """Deletes a job listing."""
        JobService._check_job_ownership(job, user)
        job_title = job.title
        job_id = job.pk
        job.delete()
        logger.warning(f"Job permanently deleted: '{job_title}' (ID: {job_id}) by {user.username}")

    @staticmethod
    def get_job_by_id(job_id: int) -> Job:
        """Resolves a Job by primary key with optimal relationship prefetching."""
        return (
            Job.objects.select_related("recruiter")
            .prefetch_related("skills", "job_required_skills__skill")
            .get(pk=job_id)
        )

    @staticmethod
    def get_job_by_slug(slug: str) -> Job:
        """Resolves a Job by unique slug with optimal relationship prefetching."""
        return (
            Job.objects.select_related("recruiter")
            .prefetch_related("skills", "job_required_skills__skill")
            .get(slug=slug)
        )

    @staticmethod
    def search_and_filter_jobs(filters: Dict[str, Any]) -> QuerySet:
        """
        Executes search, multi-faceted filtering, and sorting across active job postings.
        """
        # Base query filters for active, unexpired jobs
        now = timezone.now()
        qs = Job.objects.filter(
            status=JobStatus.ACTIVE,
            deadline__gt=now,
        ).select_related("recruiter").prefetch_related("skills")

        # Full-text style keyword search
        search_query = filters.get("q")
        if search_query:
            query = search_query.strip()
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(requirements__icontains=query)
                | Q(location__icontains=query)
                | Q(department__icontains=query)
                | Q(skills__name__icontains=query)
            ).distinct()

        # Faceted filters
        if filters.get("job_type"):
            qs = qs.filter(job_type=filters["job_type"])

        if filters.get("workplace_type"):
            qs = qs.filter(workplace_type=filters["workplace_type"])

        if filters.get("education_level"):
            qs = qs.filter(education_level=filters["education_level"])

        if filters.get("location"):
            qs = qs.filter(location__icontains=filters["location"].strip())

        if filters.get("max_experience") is not None and filters.get("max_experience") != "":
            try:
                max_exp = int(filters["max_experience"])
                qs = qs.filter(experience_min__lte=max_exp)
            except (ValueError, TypeError):
                pass

        # Sorting
        sort_by = filters.get("sort_by") or "-created_at"
        allowed_sorts = {
            "-created_at": "-created_at",
            "created_at": "created_at",
            "deadline": "deadline",
            "-salary_max": "-salary_max",
            "experience_min": "experience_min",
        }
        order_field = allowed_sorts.get(sort_by, "-created_at")
        return qs.order_by(order_field)

    @staticmethod
    def list_recruiter_jobs(recruiter, status: Optional[str] = None) -> QuerySet:
        """Returns all jobs belonging to a specific recruiter with optional status filter."""
        qs = (
            Job.objects.filter(recruiter=recruiter)
            .prefetch_related("skills")
            .order_by("-created_at")
        )
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def increment_views(job: Job) -> None:
        """Atomically increments the job view count without race conditions."""
        Job.objects.filter(pk=job.pk).update(views_count=F("views_count") + 1)
        job.refresh_from_db(fields=["views_count"])

    @staticmethod
    def _check_job_ownership(job: Job, user) -> None:
        """Internal guard ensuring only the job owner or platform superuser can mutate a job."""
        if user.is_superuser or user.role == "ADMIN":
            return
        if job.recruiter != user:
            raise PermissionDenied("You do not have permission to manage this job listing.")

