"""Unit and integration test suite for the AI screening module."""
from __future__ import annotations

import io
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfWriter

from accounts.constants import Role
from ai.ats_score import ats_scorer
from ai.constants import (
    SCORE_MAX,
    SCORE_MIN,
    TIER_HIGH_THRESHOLD,
    TIER_MEDIUM_THRESHOLD,
    TIER_STRONG_LABEL,
)
from ai.jd_parser import jd_parser
from ai.matcher import resume_matcher
from ai.models import ATSAnalysisResult
from ai.preprocess import preprocessor
from ai.ranking import candidate_ranker
from ai.recommendation import recommendation_engine
from ai.resume_parser import ai_resume_parser
from ai.services import AIService
from ai.skill_extractor import skill_extractor
from ai.validators import validate_raw_corpus, validate_score_range, validate_skill_list
from jobs.constants import EducationLevel
from jobs.models import Job, JobRequiredSkill, Skill
from resumes.models import Resume

User = get_user_model()


def create_blank_pdf() -> bytes:
    """Helper creating valid in-memory PDF."""
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class AIEngineUnitTests(TestCase):
    """Test individual AI algorithmic components, constants, and validators."""

    def test_validators(self) -> None:
        """Validate input boundaries and error handling."""
        # Valid score
        validate_score_range(Decimal("85.50"))
        validate_score_range(0)
        validate_score_range(100)

        # Invalid score
        with self.assertRaises(ValidationError):
            validate_score_range(Decimal("-5.00"))
        with self.assertRaises(ValidationError):
            validate_score_range(Decimal("105.00"))

        # Skill list validation
        validate_skill_list(["Python", "Django"])
        with self.assertRaises(ValidationError):
            validate_skill_list("not a list")
        with self.assertRaises(ValidationError):
            validate_skill_list(["Python", ""])

        # Corpus validation
        validate_raw_corpus("Valid text corpus.")
        with self.assertRaises(ValidationError):
            validate_raw_corpus("   ")

    def test_text_preprocessor(self) -> None:
        raw = "We are seeking a Senior Python & Django Developer with AWS experience!"
        tokens = preprocessor.tokenize(raw)
        self.assertIn("python", tokens)
        self.assertIn("django", tokens)

        preprocessed = preprocessor.preprocess(raw)
        self.assertNotIn("with", preprocessed)
        self.assertIn("developer", preprocessed)

    def test_skill_extractor(self) -> None:
        text = "Experienced in Python, Django REST Framework, Docker, and PostgreSQL on AWS."
        extracted = skill_extractor.extract_skills_from_text(text)
        self.assertIn("Python", extracted)
        self.assertIn("Django REST Framework", extracted)
        self.assertIn("Docker", extracted)
        self.assertIn("PostgreSQL", extracted)
        self.assertIn("AWS", extracted)

        is_match = skill_extractor.match_skill_fuzzy("react.js", ["React", "Python"])
        self.assertTrue(is_match)

    def test_jd_parser(self) -> None:
        jd_text = (
            "Senior Backend Engineer. Must have 5+ years of experience in Python and PostgreSQL. "
            "Requires a Master's degree in Computer Science."
        )
        min_exp, max_exp = jd_parser.extract_experience_requirement(jd_text)
        self.assertEqual(min_exp, 5)

        edu = jd_parser.extract_education_requirement(jd_text)
        self.assertEqual(edu, "Master's")

    def test_matcher_cosine_and_skills(self) -> None:
        resume_text = "Proficient in Python, Django, Docker, and AWS with 4 years experience."
        jd_text = "Looking for a Python and Django developer with Docker and CI/CD skills."

        cosine_sim = resume_matcher.calculate_cosine_similarity(resume_text, jd_text)
        self.assertGreater(cosine_sim, 0.0)

        candidate_skills = ["Python", "Django", "Docker", "AWS"]
        required_skills = ["Python", "Django", "Kubernetes"]
        matched, missing, suggested = resume_matcher.match_skills(candidate_skills, required_skills)

        self.assertIn("Python", matched)
        self.assertIn("Django", matched)
        self.assertIn("Kubernetes", missing)

    def test_ats_scorer_range_and_breakdown(self) -> None:
        resume_data = {
            "skills": ["Python", "Django"],
            "experience_years": 4,
            "education": ["Bachelor of Science in CS"],
            "projects": ["Built ATS with Django", "Created REST microservices"],
            "certifications": ["AWS Certified Solutions Architect"],
        }
        job_data = {
            "required_skills": ["Python", "Django", "Docker"],
            "min_experience": 3,
            "required_education": "Bachelor's",
        }
        match_data = {
            "matched_skills": ["Python", "Django"],
            "missing_skills": ["Docker"],
        }

        score_res = ats_scorer.calculate_score(resume_data, job_data, match_data)
        self.assertGreaterEqual(score_res["overall_score"], 0.0)
        self.assertLessEqual(score_res["overall_score"], 100.0)
        self.assertGreater(score_res["skills_score"], 60.0)
        self.assertGreaterEqual(score_res["experience_score"], 90.0)

    def test_candidate_ranker(self) -> None:
        candidates = [
            {"candidate_name": "Alice", "overall_score": 75.0, "skills_score": 80.0, "experience_years": 3},
            {"candidate_name": "Bob", "overall_score": 92.5, "skills_score": 95.0, "experience_years": 6},
            {"candidate_name": "Charlie", "overall_score": 60.0, "skills_score": 50.0, "experience_years": 1},
        ]
        ranked = candidate_ranker.rank_candidates(candidates)
        self.assertEqual(ranked[0]["candidate_name"], "Bob")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[0]["tier"], "Tier 1: High Fit")
        self.assertEqual(ranked[2]["candidate_name"], "Charlie")

    def test_recommendation_engine(self) -> None:
        resume_data = {
            "skills": ["Python"],
            "raw_text": "Software engineer with python experience.",
            "projects": [],
            "github": "",
            "linkedin": "",
        }
        job_data = {"required_skills": ["Python", "Docker", "AWS"]}
        match_data = {"missing_skills": ["Docker", "AWS"]}
        ats_score_data = {"overall_score": 50.0}

        recs = recommendation_engine.generate_recommendations(
            resume_data, job_data, match_data, ats_score_data
        )
        self.assertTrue(len(recs) >= 2)
        self.assertTrue(any("Docker" in r for r in recs))


class AIServiceIntegrationTests(TestCase):
    """Test AI Service facade, database persistence, and end-to-end integration."""

    def setUp(self) -> None:
        self.recruiter = User.objects.create_user(
            username="recruiter_ai",
            email="recruiter_ai@example.com",
            password="StrongPassword123!",
            role=Role.RECRUITER,
        )
        self.candidate = User.objects.create_user(
            username="candidate_ai",
            email="candidate_ai@example.com",
            password="StrongPassword123!",
            role=Role.CANDIDATE,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter,
            title="Senior Python Backend Engineer",
            description="We need an expert Python and Django backend developer with Docker and PostgreSQL.",
            requirements="Python, Django, PostgreSQL, Docker",
            experience_min=3,
            experience_max=6,
            education_level=EducationLevel.BACHELOR,
            location="Remote",
            salary_min=Decimal("100000.00"),
            salary_max=Decimal("130000.00"),
            deadline=timezone.now() + timezone.timedelta(days=30),
        )

        skill_py, _ = Skill.objects.get_or_create(name="Python")
        skill_dj, _ = Skill.objects.get_or_create(name="Django")
        skill_dk, _ = Skill.objects.get_or_create(name="Docker")

        JobRequiredSkill.objects.create(job=self.job, skill=skill_py, is_mandatory=True)
        JobRequiredSkill.objects.create(job=self.job, skill=skill_dj, is_mandatory=True)
        JobRequiredSkill.objects.create(job=self.job, skill=skill_dk, is_mandatory=True)

        self.pdf_file = SimpleUploadedFile("resume.pdf", create_blank_pdf(), content_type="application/pdf")
        self.resume = Resume.objects.create(
            candidate=self.candidate,
            file=self.pdf_file,
            file_name="resume.pdf",
            file_size=1024,
            file_format="PDF",
            raw_text="Jane Doe\njane@example.com\nSkills: Python, Django, PostgreSQL, Git\n5 years experience.\nEducation: Bachelor of Science",
            extracted_name="Jane Doe",
            extracted_email="jane@example.com",
            extracted_skills=["Python", "Django", "PostgreSQL"],
            extracted_education=["Bachelor of Science"],
            extracted_experience=[{"role": "Senior Engineer", "years": 5}],
            extracted_projects=["ATS Engine"],
            is_primary=True,
        )
        self.client = Client()

    def test_service_analyze_and_save(self) -> None:
        result = AIService.analyze_resume_against_job(self.resume, self.job, save=True)
        self.assertIsInstance(result, ATSAnalysisResult)
        self.assertGreater(result.overall_score, Decimal("50.00"))
        self.assertIn("Python", result.matched_skills)
        self.assertIn("Django", result.matched_skills)
        self.assertIn("Docker", result.missing_skills)

        db_record = ATSAnalysisResult.objects.get(resume=self.resume, job=self.job)
        self.assertEqual(db_record.overall_score, result.overall_score)

    def test_evaluation_detail_view_permissions(self) -> None:
        result = AIService.analyze_resume_against_job(self.resume, self.job, save=True)
        url = reverse("ai:evaluation_detail", kwargs={"pk": result.pk})

        self.client.force_login(self.candidate)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate ATS Analysis")

        other_user = User.objects.create_user(
            username="other_cand",
            email="other_cand@example.com",
            password="StrongPassword123!",
            role=Role.CANDIDATE,
        )
        self.client.force_login(other_user)
        resp_blocked = self.client.get(url)
        self.assertEqual(resp_blocked.status_code, 302)

    def test_ranking_leaderboard_view(self) -> None:
        AIService.analyze_resume_against_job(self.resume, self.job, save=True)
        url = reverse("ai:job_leaderboard", kwargs={"job_id": self.job.id})

        self.client.force_login(self.recruiter)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applicant Leaderboard")
        self.assertContains(response, self.candidate.email)
