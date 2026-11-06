"""
Thin view controllers for Resume management, downloading, parsing inspection, and versioning.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, FileResponse, Http404
from django.core.exceptions import PermissionDenied, ValidationError

from accounts.utils import RoleRequiredMixin
from .models import Resume
from .forms import ResumeUploadForm, ResumeReplaceForm
from .services import ResumeService

logger = logging.getLogger(__name__)


class ResumeListView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Lists all resumes uploaded by the current candidate with an inline upload form."""

    allowed_roles = ["CANDIDATE", "ADMIN"]
    template_name = "resumes/resume_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        resumes = ResumeService.get_candidate_resumes(request.user)
        form = ResumeUploadForm()
        return render(request, self.template_name, {"resumes": resumes, "form": form})


class ResumeUploadView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Processes new resume upload and initiates automatic parsing."""

    allowed_roles = ["CANDIDATE", "ADMIN"]

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                resume = ResumeService.upload_resume(
                    candidate=request.user,
                    uploaded_file=request.FILES["file"],
                    is_primary=form.cleaned_data.get("is_primary", True),
                )
                messages.success(request, f"Resume '{resume.file_name}' uploaded and parsed successfully!")
                return redirect("resumes:detail", pk=resume.pk)
            except ValidationError as err:
                messages.error(request, err.message)
            except Exception as exc:
                logger.error(f"Upload failed: {exc}", exc_info=True)
                messages.error(request, f"Upload error: {exc}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

        return redirect("resumes:list")


class ResumeDetailView(LoginRequiredMixin, View):
    """Displays semantic intelligence extracted from the candidate's resume."""

    template_name = "resumes/resume_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        resume = get_object_or_404(Resume, pk=pk)
        if not ResumeService.can_access_resume(resume, request.user):
            raise PermissionDenied("You do not have permission to view this resume.")

        replace_form = ResumeReplaceForm()
        context = {
            "resume": resume,
            "replace_form": replace_form,
            "is_owner": resume.candidate == request.user,
        }
        return render(request, self.template_name, context)


class ResumeReplaceView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Replaces an existing resume with a newer document version."""

    allowed_roles = ["CANDIDATE", "ADMIN"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        resume = get_object_or_404(Resume, pk=pk)
        form = ResumeReplaceForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                ResumeService.replace_resume(
                    resume=resume,
                    candidate=request.user,
                    new_file=request.FILES["file"],
                )
                messages.success(request, f"Resume successfully updated to Version {resume.version}!")
            except Exception as exc:
                logger.error(f"Failed to replace resume: {exc}", exc_info=True)
                messages.error(request, f"Failed to update resume: {exc}")
        else:
            messages.error(request, "Please provide a valid PDF or DOCX file under 10MB.")

        return redirect("resumes:detail", pk=resume.pk)


class ResumeDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Permanently deletes a resume."""

    allowed_roles = ["CANDIDATE", "ADMIN"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        resume = get_object_or_404(Resume, pk=pk)
        try:
            name = resume.file_name
            ResumeService.delete_resume(resume, request.user)
            messages.success(request, f"Resume '{name}' was deleted.")
        except PermissionDenied as p_err:
            messages.error(request, str(p_err))

        return redirect("resumes:list")


class ResumeDownloadView(LoginRequiredMixin, View):
    """Securely streams the resume binary to authorized candidates, recruiters, and admins."""

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        resume = get_object_or_404(Resume, pk=pk)
        if not ResumeService.can_access_resume(resume, request.user):
            raise PermissionDenied("You do not have permission to download this document.")

        try:
            response = FileResponse(resume.file.open("rb"), as_attachment=True, filename=resume.file_name)
            return response
        except FileNotFoundError:
            raise Http404("Resume file not found on storage.")


class ResumeHistoryView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Renders version history and superseded snapshots for a candidate's resume."""

    allowed_roles = ["CANDIDATE", "ADMIN"]
    template_name = "resumes/resume_history.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        resume = get_object_or_404(Resume, pk=pk)
        ResumeService._verify_candidate_ownership(resume, request.user)

        history_records = resume.history_records.all()
        return render(request, self.template_name, {"resume": resume, "history": history_records})

