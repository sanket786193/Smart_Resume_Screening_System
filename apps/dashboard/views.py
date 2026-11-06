"""
Views for the Dashboard and Enterprise Landing Page.
"""
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class LandingPageView(View):
    """
    Public flagship landing page showcasing the AI ATS Platform,
    interactive prompt bar, and live ATS matching simulator.
    """
    template_name = "landing.html"

    def get(self, request):
        return render(request, self.template_name)


class DashboardHomeView(LoginRequiredMixin, View):
    """
    Smart router that directs users to their respective role workspace:
    - Candidate -> Candidate profile & application tracker
    - Recruiter -> Job listings & talent pipelines
    - Admin -> Audit logs & system management
    """
    def get(self, request):
        user = request.user
        if user.is_candidate:
            return redirect("accounts:profile")
        elif user.is_recruiter:
            return redirect("accounts:profile")
        elif user.is_admin_user:
            return redirect("accounts:audit_logs")
        return redirect("accounts:profile")
