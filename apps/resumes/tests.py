"""
Comprehensive test suite for the Resumes application covering Models, Validators,
Parsing Engine, Services, Views, and Security Access Controls.
"""
import io
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse

from .models import Resume, ResumeHistory
from .constants import ParsingStatus, ResumeFormat
from .validators import validate_resume_file
from .parser import ResumeParser
from .services import ResumeService

User = get_user_model()


class ResumeValidatorTests(TestCase):
    """Unit tests for upload file validators."""

    def test_valid_pdf_file_passes(self):
        file = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 simulated pdf stream", content_type="application/pdf")
        validate_resume_file(file)

    def test_valid_docx_file_passes(self):
        file = SimpleUploadedFile("sample.docx", b"PK simulated docx stream", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        validate_resume_file(file)

    def test_invalid_extension_rejected(self):
        file = SimpleUploadedFile("virus.exe", b"executable bytes", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_resume_file(file)

    def test_empty_file_rejected(self):
        file = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_resume_file(file)


class ResumeParserEngineTests(TestCase):
    """Unit tests for regex and rule-based semantic extraction."""

    SAMPLE_RESUME_TEXT = """
    Alex Smith
    alex.smith@example.com | (555) 234-5678 | San Francisco, CA
    https://github.com/alexsmith | https://linkedin.com/in/alexsmith

    PROFESSIONAL SUMMARY
    Senior Software Engineer with 6 years of expertise building scalable distributed systems with Python and Django.

    TECHNICAL SKILLS
    Languages: Python, JavaScript, TypeScript, SQL, Bash
    Frameworks: Django, FastAPI, React, Node.js, PyTorch
    Databases & Cloud: PostgreSQL, Redis, Docker, Kubernetes, AWS, Git, CI/CD

    EXPERIENCE
    Senior Software Engineer at CloudCorp (2021 - Present)
    - Architected REST APIs and microservices.
    Backend Developer at DataTech (2018 - 2021)
    - Built data ingestion pipelines using Django and PostgreSQL.

    EDUCATION
    Bachelor of Science in Computer Science - University of California

    CERTIFICATIONS
    AWS Certified Solutions Architect

    LANGUAGES
    English, Spanish
    """

    def test_parser_extracts_all_required_entities(self):
        parsed = ResumeParser.parse_text(self.SAMPLE_RESUME_TEXT)

        self.assertEqual(parsed["name"], "Alex Smith")
        self.assertEqual(parsed["email"], "alex.smith@example.com")
        self.assertEqual(parsed["phone"], "(555) 234-5678")
        self.assertEqual(parsed["github"], "https://github.com/alexsmith")
        self.assertEqual(parsed["linkedin"], "https://linkedin.com/in/alexsmith")

        # Skills verification
        skills = parsed["skills"]
        self.assertIn("Python", skills)
        self.assertIn("Django", skills)
        self.assertIn("PostgreSQL", skills)
        self.assertIn("Docker", skills)
        self.assertIn("AWS", skills)
        self.assertIn("React", skills)

        # Education & Experience
        self.assertTrue(any("Bachelor" in edu for edu in parsed["education"]))
        self.assertTrue(any("Software Engineer" in exp for exp in parsed["experience"]))
        self.assertIn("AWS Certified Solutions Architect", parsed["certifications"])
        self.assertIn("English", parsed["languages"])
        self.assertIn("Spanish", parsed["languages"])


class ResumeServiceTests(TestCase):
    """Unit tests for ResumeService business logic and transactions."""

    def setUp(self):
        self.candidate = User.objects.create_user(
            username="candidate_cv",
            email="cand_cv@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        self.other_candidate = User.objects.create_user(
            username="other_cand",
            email="other@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        self.recruiter = User.objects.create_user(
            username="recruiter_cv",
            email="rec_cv@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
        )

    def _create_mock_resume_file(self, filename="resume.pdf"):
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        return SimpleUploadedFile(
            filename,
            buf.read(),
            content_type="application/pdf",
        )

    def test_upload_resume_success(self):
        file = self._create_mock_resume_file()
        resume = ResumeService.upload_resume(self.candidate, file, is_primary=True)

        self.assertIsNotNone(resume.pk)
        self.assertEqual(resume.version, 1)
        self.assertTrue(resume.is_primary)
        self.assertEqual(resume.file_format, ResumeFormat.PDF)

    def test_recruiter_cannot_upload_candidate_resume(self):
        file = self._create_mock_resume_file()
        with self.assertRaises(PermissionDenied):
            ResumeService.upload_resume(self.recruiter, file)

    def test_replace_resume_creates_history_record(self):
        file1 = self._create_mock_resume_file("resume_v1.pdf")
        resume = ResumeService.upload_resume(self.candidate, file1, is_primary=True)
        self.assertEqual(resume.version, 1)

        file2 = self._create_mock_resume_file("resume_v2.pdf")
        updated_resume = ResumeService.replace_resume(resume, self.candidate, file2)

        self.assertEqual(updated_resume.version, 2)
        self.assertEqual(updated_resume.file_name, "resume_v2.pdf")
        self.assertEqual(ResumeHistory.objects.filter(resume=resume).count(), 1)
        archive = ResumeHistory.objects.get(resume=resume)
        self.assertEqual(archive.version, 1)
        self.assertEqual(archive.file_name, "resume_v1.pdf")

    def test_access_permissions(self):
        file = self._create_mock_resume_file()
        resume = ResumeService.upload_resume(self.candidate, file)

        # Owner has access
        self.assertTrue(ResumeService.can_access_resume(resume, self.candidate))
        # Recruiter has access to review
        self.assertTrue(ResumeService.can_access_resume(resume, self.recruiter))
        # Other candidate does not have access
        self.assertFalse(ResumeService.can_access_resume(resume, self.other_candidate))


class ResumeViewsTests(TestCase):
    """Integration tests for Resume views."""

    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username="view_candidate",
            email="view_cand@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        self.file = SimpleUploadedFile("test.pdf", buf.read(), content_type="application/pdf")
        self.resume = ResumeService.upload_resume(self.candidate, self.file)

    def test_candidate_can_view_resumes_list(self):
        self.client.login(username="view_candidate", password="Password123!")
        res = self.client.get(reverse("resumes:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "test.pdf")

    def test_candidate_can_view_resume_detail(self):
        self.client.login(username="view_candidate", password="Password123!")
        res = self.client.get(reverse("resumes:detail", kwargs={"pk": self.resume.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "test.pdf")

    def test_candidate_can_download_resume(self):
        self.client.login(username="view_candidate", password="Password123!")
        res = self.client.get(reverse("resumes:download", kwargs={"pk": self.resume.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
