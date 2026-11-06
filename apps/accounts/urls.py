"""
URL Routing configuration for Accounts application.
"""
from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordConfirmView,
    ChangePasswordView,
    ProfileUpdateView,
    UserDeactivateView,
    AuditLogListView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/<str:uidb64>/<str:token>/", ResetPasswordConfirmView.as_view(), name="reset_password_confirm"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path("deactivate/", UserDeactivateView.as_view(), name="deactivate"),
    path("audit-logs/", AuditLogListView.as_view(), name="audit_logs"),
]

