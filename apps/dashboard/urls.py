"""Dashboard application URL routing."""
from django.urls import path
from .views import DashboardHomeView, LandingPageView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="home"),
    path("landing/", LandingPageView.as_view(), name="landing"),
]
