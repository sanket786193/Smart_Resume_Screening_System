"""
Thin view controllers for the Jobs application.
Delegates all database filtering, mutations, and authorizations to JobService.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError

from accounts.utils import RoleRequiredMixin
from .models import Job
from .forms import JobCreateUpdateForm, JobFilterForm
from .services import JobService
from .utils import get_skills_as_comma_separated
from .constants import DEFAULT_PAGE_SIZE, JobStatus

logger = logging.getLogger(__name__)


class JobListView(View):
    """Public and Candidate-accessible job search directory with faceted filters."""

    template_name = "jobs/job_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        filter_form = JobFilterForm(request.GET)
        filters = {}
        if filter_form.is_valid():
            filters = filter_form.cleaned_data

        jobs_qs = JobService.search_and_filter_jobs(filters)

        paginator = Paginator(jobs_qs, DEFAULT_PAGE_SIZE)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "filter_form": filter_form,
            "total_count": paginator.count,
        }
        return render(request, self.template_name, context)


class JobDetailView(View):
    """Detailed job description page showing required skills, qualifications, and apply button."""

    template_name = "jobs/job_detail.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        try:
            job = JobService.get_job_by_slug(slug)
        except Job.DoesNotExist:
            return render(request, "404.html", status=404)

        # Increment view count
        JobService.increment_views(job)

        context = {
            "job": job,
            "required_skills": job.job_required_skills.select_related("skill").all(),
            "is_recruiter_owner": request.user.is_authenticated and (job.recruiter == request.user or request.user.is_superuser),
        }
        return render(request, self.template_name, context)


class JobCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Enables Recruiters to author and publish a new job opening."""

    allowed_roles = ["RECRUITER", "ADMIN"]
    template_name = "jobs/job_form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = JobCreateUpdateForm()
        return render(request, self.template_name, {"form": form, "is_edit": False})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = JobCreateUpdateForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            skills_str = cleaned.pop("skills_input")
            try:
                job = JobService.create_job(
                    recruiter=request.user,
                    job_data=cleaned,
                    skills_str=skills_str,
                )
                messages.success(request, f"Job '{job.title}' was successfully created!")
                return redirect(job.get_absolute_url())
            except ValidationError as err:
                form.add_error(None, err.message)
            except Exception as exc:
                logger.error(f"Failed to create job: {exc}", exc_info=True)
                messages.error(request, f"Could not create job: {exc}")

        return render(request, self.template_name, {"form": form, "is_edit": False})


class JobUpdateView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Allows a job's authoring Recruiter or Admin to update posting details."""

    allowed_roles = ["RECRUITER", "ADMIN"]
    template_name = "jobs/job_form.html"

    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        job = get_object_or_404(Job, slug=slug)
        JobService._check_job_ownership(job, request.user)

        initial_skills = get_skills_as_comma_separated(job)
        form = JobCreateUpdateForm(instance=job, initial={"skills_input": initial_skills})
        return render(request, self.template_name, {"form": form, "job": job, "is_edit": True})

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        job = get_object_or_404(Job, slug=slug)
        JobService._check_job_ownership(job, request.user)

        form = JobCreateUpdateForm(request.POST, instance=job)
        if form.is_valid():
            cleaned = form.cleaned_data
            skills_str = cleaned.pop("skills_input")
            try:
                JobService.update_job(
                    job=job,
                    job_data=cleaned,
                    skills_str=skills_str,
                    user=request.user,
                )
                messages.success(request, f"Job '{job.title}' updated successfully.")
                return redirect(job.get_absolute_url())
            except ValidationError as err:
                form.add_error(None, err.message)
            except Exception as exc:
                logger.error(f"Failed to update job: {exc}", exc_info=True)
                messages.error(request, f"Could not update job: {exc}")

        return render(request, self.template_name, {"form": form, "job": job, "is_edit": True})


class JobDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Allows Recruiter or Admin to delete a job listing."""

    allowed_roles = ["RECRUITER", "ADMIN"]

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        job = get_object_or_404(Job, slug=slug)
        try:
            job_title = job.title
            JobService.delete_job(job, request.user)
            messages.success(request, f"Job '{job_title}' was permanently deleted.")
        except PermissionDenied as p_err:
            messages.error(request, str(p_err))

        return redirect("jobs:recruiter_manage")


class JobToggleStatusView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Allows Recruiter to rapidly toggle a job between Active and Closed."""

    allowed_roles = ["RECRUITER", "ADMIN"]

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        job = get_object_or_404(Job, slug=slug)
        try:
            if job.status == JobStatus.ACTIVE:
                JobService.close_job(job, request.user)
                messages.info(request, f"Job '{job.title}' is now closed to new applications.")
            else:
                JobService.reopen_job(job, request.user)
                messages.success(request, f"Job '{job.title}' has been reopened!")
        except Exception as exc:
            messages.error(request, f"Failed to change status: {exc}")

        return redirect("jobs:recruiter_manage")


class RecruiterJobManageView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Recruiter dashboard listing all postings authored by the current recruiter."""

    allowed_roles = ["RECRUITER", "ADMIN"]
    template_name = "jobs/recruiter_manage.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        status_filter = request.GET.get("status")
        jobs_qs = JobService.list_recruiter_jobs(request.user, status=status_filter)

        paginator = Paginator(jobs_qs, 15)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "status_filter": status_filter,
            "total_jobs": jobs_qs.count(),
        }
        return render(request, self.template_name, context)
