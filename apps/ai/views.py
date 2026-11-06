"""Thin views for AI screening, matching, and ranking."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.constants import Role
from ai.models import ATSAnalysisResult
from ai.services import AIService
from jobs.models import Job
from resumes.models import Resume


class EvaluateResumeView(LoginRequiredMixin, View):
    """Trigger AI resume screening against a target job."""

    def post(self, request: HttpRequest, resume_id: int, job_id: int) -> HttpResponse:
        resume = get_object_or_404(Resume, id=resume_id)
        job = get_object_or_404(Job, id=job_id)

        owner = getattr(resume, "candidate", getattr(resume, "user", None))
        if request.user.role == Role.CANDIDATE and owner != request.user:
            messages.error(request, "Permission denied.")
            return redirect("resumes:list")

        result = AIService.analyze_resume_against_job(resume=resume, job=job, save=True)
        messages.success(request, f"AI evaluation complete! ATS Score: {result.overall_score}%")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "overall_score": float(result.overall_score),
                "match_percentage": float(result.match_percentage),
                "tier": result.tier,
                "matched_skills": result.matched_skills,
                "missing_skills": result.missing_skills,
            })

        return redirect("ai:evaluation_detail", pk=result.pk)


class EvaluationDetailView(LoginRequiredMixin, View):
    """Display comprehensive ATS evaluation breakdown and AI recommendations."""

    template_name = "ai/evaluation_detail.html"

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        result = get_object_or_404(
            ATSAnalysisResult.objects.select_related("resume", "job", "job__recruiter"),
            pk=pk,
        )

        owner = getattr(result.resume, "candidate", getattr(result.resume, "user", None))
        if request.user.role == Role.CANDIDATE and owner != request.user:
            messages.error(request, "You do not have permission to view this report.")
            return redirect("resumes:list")

        context = {
            "result": result,
            "resume": result.resume,
            "candidate_user": owner,
            "job": result.job,
            "tier": result.tier,
        }
        return render(request, self.template_name, context)


class JobRankingLeaderboardView(LoginRequiredMixin, View):
    """Recruiter/Admin view displaying AI-ranked candidate leaderboard for a specific job."""

    template_name = "ai/ranking_leaderboard.html"

    def get(self, request: HttpRequest, job_id: int) -> HttpResponse:
        job = get_object_or_404(Job, id=job_id)

        if request.user.role == Role.CANDIDATE:
            messages.error(request, "Candidate access restricted.")
            return redirect("jobs:list")

        if request.user.role == Role.RECRUITER and job.recruiter != request.user:
            messages.error(request, "You can only view applicant rankings for your own jobs.")
            return redirect("jobs:recruiter_manage")

        ranked_candidates = AIService.rank_candidates_for_job(job=job)

        context = {
            "job": job,
            "ranked_candidates": ranked_candidates,
            "total_candidates": len(ranked_candidates),
        }
        return render(request, self.template_name, context)


class BatchScreenJobView(LoginRequiredMixin, View):
    """Run batch screening for all candidates against a job."""

    def post(self, request: HttpRequest, job_id: int) -> HttpResponse:
        job = get_object_or_404(Job, id=job_id)

        if request.user.role == Role.CANDIDATE:
            messages.error(request, "Access restricted.")
            return redirect("jobs:list")

        count = AIService.batch_screen_job_resumes(job)
        messages.success(request, f"AI Batch Screening completed for {count} candidates!")
        return redirect("ai:job_leaderboard", job_id=job.id)
