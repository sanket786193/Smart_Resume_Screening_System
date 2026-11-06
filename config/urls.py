"""
Root URL Configuration for Smart Resume Screening & ATS System.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import LandingPageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", LandingPageView.as_view(), name="root"),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("jobs/", include("jobs.urls", namespace="jobs")),
    path("resumes/", include("resumes.urls", namespace="resumes")),
    path("applications/", include("applications.urls", namespace="applications")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("reports/", include("reports.urls", namespace="reports")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path("ai/", include("ai.urls", namespace="ai")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler403 = "accounts.views.custom_permission_denied_view"
handler404 = "accounts.views.custom_page_not_found_view"
handler500 = "accounts.views.custom_server_error_view"

