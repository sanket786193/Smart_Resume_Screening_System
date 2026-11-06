"""
URL Routing configuration for the Resumes application.
"""
from django.urls import path
from .views import (
    ResumeListView,
    ResumeUploadView,
    ResumeDetailView,
    ResumeReplaceView,
    ResumeDeleteView,
    ResumeDownloadView,
    ResumeHistoryView,
)

app_name = "resumes"

urlpatterns = [
    path("", ResumeListView.as_view(), name="list"),
    path("upload/", ResumeUploadView.as_view(), name="upload"),
    path("<int:pk>/", ResumeDetailView.as_view(), name="detail"),
    path("<int:pk>/replace/", ResumeReplaceView.as_view(), name="replace"),
    path("<int:pk>/delete/", ResumeDeleteView.as_view(), name="delete"),
    path("<int:pk>/download/", ResumeDownloadView.as_view(), name="download"),
    path("<int:pk>/history/", ResumeHistoryView.as_view(), name="history"),
]
