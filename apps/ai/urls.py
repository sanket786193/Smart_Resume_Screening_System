"""URL routing for the AI screening module."""
from __future__ import annotations

from django.urls import path
from ai import views

app_name = "ai"

urlpatterns = [
    path("evaluate/<int:resume_id>/<int:job_id>/", views.EvaluateResumeView.as_view(), name="evaluate_resume"),
    path("result/<int:pk>/", views.EvaluationDetailView.as_view(), name="evaluation_detail"),
    path("ranking/<int:job_id>/", views.JobRankingLeaderboardView.as_view(), name="job_leaderboard"),
    path("batch-screen/<int:job_id>/", views.BatchScreenJobView.as_view(), name="batch_screen_job"),
]
