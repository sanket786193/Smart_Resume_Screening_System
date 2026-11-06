"""
URL Routing configuration for the Jobs application.
"""
from django.urls import path
from .views import (
    JobListView,
    JobDetailView,
    JobCreateView,
    JobUpdateView,
    JobDeleteView,
    JobToggleStatusView,
    RecruiterJobManageView,
)

app_name = "jobs"

urlpatterns = [
    path("", JobListView.as_view(), name="list"),
    path("create/", JobCreateView.as_view(), name="create"),
    path("manage/", RecruiterJobManageView.as_view(), name="recruiter_manage"),
    path("<slug:slug>/", JobDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", JobUpdateView.as_view(), name="update"),
    path("<slug:slug>/delete/", JobDeleteView.as_view(), name="delete"),
    path("<slug:slug>/toggle-status/", JobToggleStatusView.as_view(), name="toggle_status"),
]
