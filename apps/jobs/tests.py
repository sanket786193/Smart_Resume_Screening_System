"""
Comprehensive test suite for the Jobs application covering Models, Validators,
Services, Views, Search & Filtering, and Role-Based Access Control.
"""
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse

from .models import Job, Skill, JobRequiredSkill
from .constants import JobType, WorkplaceType, JobStatus, EducationLevel
from .validators import validate_future_deadline, validate_salary_range, validate_experience_range
from .services import JobService
from .utils import parse_skills_string, sync_job_skills

User = get_user_model()


class JobModelTests(TestCase):
    """Unit tests for Job and Skill models."""

    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="recruiter_test",
            email="recruiter_test@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
        )

    def test_job_slug_generation_and_uniqueness(self):
        deadline = timezone.now() + timedelta(days=30)
        job1 = Job.objects.create(
            recruiter=self.recruiter,
            title="Senior Python Architect",
            location="New York",
            description="Leading backend systems",
            deadline=deadline,
        )
        self.assertIn("senior-python-architect-new-york", job1.slug)

        job2 = Job.objects.create(
            recruiter=self.recruiter,
            title="Senior Python Architect",
            location="New York",
            description="Duplicate title testing",
            deadline=deadline,
        )
        self.assertNotEqual(job1.slug, job2.slug)
        self.assertTrue(job2.slug.startswith("senior-python-architect-new-york-"))

    def test_job_is_active_and_days_remaining(self):
        future_deadline = timezone.now() + timedelta(days=15)
        job = Job.objects.create(
            recruiter=self.recruiter,
            title="Backend Dev",
            location="Remote",
            description="Django backend",
            deadline=future_deadline,
            status=JobStatus.ACTIVE,
        )
        self.assertTrue(job.is_active)
        self.assertGreaterEqual(job.days_remaining, 14)

        job.status = JobStatus.CLOSED
        job.save()
        self.assertFalse(job.is_active)


class JobValidatorsTests(TestCase):
    """Unit tests for validator rules."""

    def test_deadline_must_be_in_future(self):
        past_deadline = timezone.now() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            validate_future_deadline(past_deadline)

    def test_salary_range_validation(self):
        with self.assertRaises(ValidationError):
            validate_salary_range(min_salary=100000, max_salary=50000)

        with self.assertRaises(ValidationError):
            validate_salary_range(min_salary=-10, max_salary=50000)

        # Valid range should not raise
        validate_salary_range(min_salary=60000, max_salary=90000)

    def test_experience_range_validation(self):
        with self.assertRaises(ValidationError):
            validate_experience_range(min_exp=5, max_exp=2)

        with self.assertRaises(ValidationError):
            validate_experience_range(min_exp=-1, max_exp=5)


class JobServiceTests(TestCase):
    """Unit tests for JobService business logic and transactions."""

    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="recruiter_srv",
            email="rec_srv@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
        )
        self.candidate = User.objects.create_user(
            username="candidate_srv",
            email="cand_srv@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )

    def test_create_job_with_skills_success(self):
        deadline = timezone.now() + timedelta(days=20)
        job_data = {
            "title": "Django Backend Lead",
            "department": "Engineering",
            "description": "High throughput systems",
            "location": "San Francisco",
            "job_type": JobType.FULL_TIME,
            "workplace_type": WorkplaceType.HYBRID,
            "experience_min": 4,
            "experience_max": 8,
            "education_level": EducationLevel.BACHELOR,
            "deadline": deadline,
        }
        skills_str = "Python, Django, PostgreSQL, Docker, AWS"

        job = JobService.create_job(
            recruiter=self.recruiter,
            job_data=job_data,
            skills_str=skills_str,
        )
        self.assertIsNotNone(job.pk)
        self.assertEqual(job.skills.count(), 5)
        self.assertTrue(Skill.objects.filter(name="Python").exists())
        self.assertTrue(JobRequiredSkill.objects.filter(job=job, skill__name="Python", is_mandatory=True).exists())

    def test_candidate_cannot_create_job(self):
        deadline = timezone.now() + timedelta(days=10)
        job_data = {
            "title": "Unauthorized Role Job",
            "description": "Attempted by Candidate",
            "location": "Remote",
            "deadline": deadline,
        }
        with self.assertRaises(PermissionDenied):
            JobService.create_job(
                recruiter=self.candidate,
                job_data=job_data,
                skills_str="Python",
            )

    def test_update_job_and_reopen_close(self):
        deadline = timezone.now() + timedelta(days=15)
        job = JobService.create_job(
            recruiter=self.recruiter,
            job_data={"title": "DevOps Engineer", "description": "K8s and Terraform", "location": "Remote", "deadline": deadline},
            skills_str="Docker, Kubernetes",
        )

        # Update skills and title
        updated_job = JobService.update_job(
            job=job,
            job_data={"title": "Lead Cloud DevOps Engineer"},
            skills_str="Kubernetes, Terraform, AWS, Golang",
            user=self.recruiter,
        )
        self.assertEqual(updated_job.title, "Lead Cloud DevOps Engineer")
        self.assertEqual(updated_job.skills.count(), 4)
        self.assertFalse(updated_job.skills.filter(name="Docker").exists())

        # Close and reopen
        JobService.close_job(updated_job, self.recruiter)
        self.assertEqual(updated_job.status, JobStatus.CLOSED)

        JobService.reopen_job(updated_job, self.recruiter)
        self.assertEqual(updated_job.status, JobStatus.ACTIVE)

    def test_search_and_filter_jobs(self):
        deadline = timezone.now() + timedelta(days=25)
        job1 = JobService.create_job(
            recruiter=self.recruiter,
            job_data={
                "title": "Machine Learning Engineer",
                "description": "NLP and LLM architectures",
                "location": "Boston, MA",
                "job_type": JobType.FULL_TIME,
                "experience_min": 3,
                "deadline": deadline,
            },
            skills_str="Python, PyTorch, Transformers, NLP",
        )
        job2 = JobService.create_job(
            recruiter=self.recruiter,
            job_data={
                "title": "Frontend React Developer",
                "description": "Next.js and Tailwind",
                "location": "Remote",
                "job_type": JobType.CONTRACT,
                "experience_min": 1,
                "deadline": deadline,
            },
            skills_str="JavaScript, React, TypeScript, Tailwind",
        )

        # Search for NLP
        results_nlp = JobService.search_and_filter_jobs({"q": "PyTorch"})
        self.assertEqual(results_nlp.count(), 1)
        self.assertEqual(results_nlp.first().pk, job1.pk)

        # Filter by job type
        results_contract = JobService.search_and_filter_jobs({"job_type": JobType.CONTRACT})
        self.assertEqual(results_contract.count(), 1)
        self.assertEqual(results_contract.first().pk, job2.pk)


class JobViewsTests(TestCase):
    """Integration tests for Job Views and RBAC enforcement."""

    def setUp(self):
        self.client = Client()
        self.recruiter = User.objects.create_user(
            username="recruiter_view",
            email="rec_view@example.com",
            password="Password123!",
            role=User.Role.RECRUITER,
        )
        self.candidate = User.objects.create_user(
            username="candidate_view",
            email="cand_view@example.com",
            password="Password123!",
            role=User.Role.CANDIDATE,
        )
        deadline = timezone.now() + timedelta(days=20)
        self.job = JobService.create_job(
            recruiter=self.recruiter,
            job_data={"title": "Staff Backend Engineer", "description": "High scale architecture", "location": "Austin, TX", "deadline": deadline},
            skills_str="Python, Django, Redis",
        )

    def test_public_can_view_job_list_and_detail(self):
        res = self.client.get(reverse("jobs:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Staff Backend Engineer")

        res_detail = self.client.get(reverse("jobs:detail", kwargs={"slug": self.job.slug}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Staff Backend Engineer")

    def test_candidate_forbidden_from_job_create(self):
        self.client.login(username="candidate_view", password="Password123!")
        res = self.client.get(reverse("jobs:create"))
        self.assertEqual(res.status_code, 403)

    def test_recruiter_can_access_job_create_and_manage(self):
        self.client.login(username="recruiter_view", password="Password123!")
        res_create = self.client.get(reverse("jobs:create"))
        self.assertEqual(res_create.status_code, 200)

        res_manage = self.client.get(reverse("jobs:recruiter_manage"))
        self.assertEqual(res_manage.status_code, 200)
        self.assertContains(res_manage, "Staff Backend Engineer")

