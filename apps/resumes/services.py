"""
Service Layer for Resume Management, Versioning, and Automated Extraction Processing.
Encapsulates all file transactions and parsing orchestration.
"""
import os
import logging
from typing import Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet

from .models import Resume, ResumeHistory
from .constants import ParsingStatus, ResumeFormat
from .validators import validate_resume_file
from .utils import extract_document_text
from .parser import ResumeParser

logger = logging.getLogger(__name__)


class ResumeService:
    """Encapsulates all business logic for resume uploading, parsing, versioning, and lifecycle."""

    @staticmethod
    @transaction.atomic
    def upload_resume(candidate, uploaded_file, is_primary: bool = True) -> Resume:
        """
        Validates, persists, and asynchronously/synchronously parses candidate resumes.
        If marked as primary, unsets previous primary resumes for this candidate.
        """
        if not getattr(candidate, "is_candidate", False) and not candidate.is_superuser:
            raise PermissionDenied("Only Candidates can upload resumes.")

        validate_resume_file(uploaded_file)

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        file_format = ResumeFormat.PDF if ext == ".pdf" else ResumeFormat.DOCX

        if is_primary:
            Resume.objects.filter(candidate=candidate).update(is_primary=False)

        resume = Resume.objects.create(
            candidate=candidate,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_format=file_format,
            is_primary=is_primary,
            version=1,
            parsing_status=ParsingStatus.PENDING,
        )

        # Trigger immediate extraction pipeline
        ResumeService._execute_parsing(resume)
        return resume

    @staticmethod
    @transaction.atomic
    def replace_resume(resume: Resume, candidate, new_file) -> Resume:
        """
        Replaces an existing resume with a newer version.
        Archives the old version into ResumeHistory before executing re-parsing.
        """
        ResumeService._verify_candidate_ownership(resume, candidate)
        validate_resume_file(new_file)

        # 1. Archive current version to ResumeHistory
        ResumeHistory.objects.create(
            candidate=candidate,
            resume=resume,
            file=resume.file,
            file_name=resume.file_name,
            file_size=resume.file_size,
            version=resume.version,
        )

        # 2. Update with new file and increment version
        ext = os.path.splitext(new_file.name)[1].lower()
        resume.file = new_file
        resume.file_name = new_file.name
        resume.file_size = new_file.size
        resume.file_format = ResumeFormat.PDF if ext == ".pdf" else ResumeFormat.DOCX
        resume.version += 1
        resume.parsing_status = ParsingStatus.PENDING
        resume.save()

        # 3. Re-run parsing pipeline
        ResumeService._execute_parsing(resume)
        return resume

    @staticmethod
    def delete_resume(resume: Resume, candidate) -> None:
        """Permanently deletes a resume and its underlying disk storage."""
        ResumeService._verify_candidate_ownership(resume, candidate)
        file_path = resume.file.path if resume.file else None
        resume_name = resume.file_name

        resume.delete()

        # Delete physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as err:
                logger.warning(f"Failed to delete disk file {file_path}: {err}")

        logger.info(f"Resume '{resume_name}' deleted by candidate {candidate.username}")

    @staticmethod
    def get_candidate_resumes(candidate) -> QuerySet:
        """Returns all resumes belonging to a candidate sorted with primary first."""
        return Resume.objects.filter(candidate=candidate).order_by("-is_primary", "-updated_at")

    @staticmethod
    def get_primary_resume(candidate) -> Optional[Resume]:
        """Resolves the active default resume for rapid job application."""
        return Resume.objects.filter(candidate=candidate, is_primary=True).first()

    @staticmethod
    def can_access_resume(resume: Resume, user) -> bool:
        """
        RBAC security guard:
        - Candidate owner has full access.
        - Superusers and Admins have full access.
        - Verified Recruiters can inspect candidate resumes if reviewing applications.
        """
        if not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, "is_admin_user", False):
            return True
        if resume.candidate == user:
            return True
        if getattr(user, "is_recruiter", False):
            return True
        return False

    @staticmethod
    def _execute_parsing(resume: Resume) -> None:
        """Extracts text, applies OCR fallback if scanned, and maps semantic fields."""
        try:
            file_path = resume.file.path
            raw_text, is_ocr = extract_document_text(file_path)

            if not raw_text.strip():
                resume.parsing_status = ParsingStatus.FAILED
                resume.parsing_error = "Could not extract readable text from document."
                resume.save()
                return

            parsed_data = ResumeParser.parse_text(raw_text)

            resume.raw_text = raw_text
            resume.extracted_name = parsed_data.get("name", "")
            resume.extracted_email = parsed_data.get("email", "")
            resume.extracted_phone = parsed_data.get("phone", "")
            resume.extracted_skills = parsed_data.get("skills", [])
            resume.extracted_education = parsed_data.get("education", [])
            resume.extracted_experience = parsed_data.get("experience", [])
            resume.extracted_projects = parsed_data.get("projects", [])
            resume.extracted_certifications = parsed_data.get("certifications", [])
            resume.extracted_languages = parsed_data.get("languages", [])
            resume.extracted_github = parsed_data.get("github", "")
            resume.extracted_linkedin = parsed_data.get("linkedin", "")

            resume.parsing_status = ParsingStatus.OCR_PROCESSED if is_ocr else ParsingStatus.SUCCESS
            resume.parsing_error = ""
            resume.save()
            logger.info(f"Resume {resume.pk} parsed successfully ({resume.parsing_status})")

        except Exception as exc:
            logger.error(f"Error executing parsing on resume {resume.pk}: {exc}", exc_info=True)
            resume.parsing_status = ParsingStatus.FAILED
            resume.parsing_error = str(exc)
            resume.save()

    @staticmethod
    def _verify_candidate_ownership(resume: Resume, user) -> None:
        """Internal guard restricting mutations strictly to the resume's owner or admin."""
        if user.is_superuser or getattr(user, "is_admin_user", False):
            return
        if resume.candidate != user:
            raise PermissionDenied("You do not have permission to modify this resume.")

