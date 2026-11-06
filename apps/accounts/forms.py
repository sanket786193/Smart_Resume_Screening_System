"""
Forms for user registration, authentication, profile editing, and password lifecycle.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import CandidateProfile, RecruiterProfile
from .utils import validate_profile_photo

User = get_user_model()


class UserRegistrationForm(forms.Form):
    """Public registration form restricted to Candidate and Recruiter roles."""

    ROLE_CHOICES = [
        (User.Role.CANDIDATE, "Candidate (Looking for opportunities)"),
        (User.Role.RECRUITER, "Recruiter (Hiring talent)"),
    ]

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Choose username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
    )
    phone_number = forms.CharField(
        max_length=17,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+1234567890"}),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter strong password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Re-enter password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please pick another.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                validate_password(password)

        return cleaned_data


class UserLoginForm(forms.Form):
    """Login form accepting either username or registered email address."""

    username_or_email = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Enter username or email", "autofocus": True}
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )


class UserProfileUpdateForm(forms.ModelForm):
    """General user identity updates including avatar upload."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number", "bio", "profile_photo"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "profile_photo": forms.FileInput(attrs={"class": "form-control"}),
        }

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size"):
            validate_profile_photo(photo)
        return photo


class CandidateProfileForm(forms.ModelForm):
    """Candidate-specific employment background and links."""

    class Meta:
        model = CandidateProfile
        fields = [
            "current_job_title",
            "experience_years",
            "education_level",
            "expected_salary",
            "preferred_location",
            "linkedin_url",
            "github_url",
            "portfolio_url",
        ]
        widgets = {
            "current_job_title": forms.TextInput(attrs={"class": "form-control"}),
            "experience_years": forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
            "education_level": forms.Select(attrs={"class": "form-select"}),
            "expected_salary": forms.NumberInput(attrs={"class": "form-control"}),
            "preferred_location": forms.TextInput(attrs={"class": "form-control"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://linkedin.com/in/..."}),
            "github_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://github.com/..."}),
            "portfolio_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }


class RecruiterProfileForm(forms.ModelForm):
    """Recruiter-specific organizational attributes."""

    class Meta:
        model = RecruiterProfile
        fields = ["company_name", "company_website", "department", "position", "company_size"]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_website": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "department": forms.TextInput(attrs={"class": "form-control"}),
            "position": forms.TextInput(attrs={"class": "form-control"}),
            "company_size": forms.Select(attrs={"class": "form-select"}),
        }


class CustomPasswordResetForm(forms.Form):
    """Email prompt for forgotten password link requests."""

    email = forms.EmailField(
        label="Account Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter registered email", "autofocus": True}
        ),
    )


class CustomSetPasswordForm(forms.Form):
    """Password reset completion form with verification."""

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                validate_password(new_password)

        return cleaned_data


class CustomPasswordChangeForm(forms.Form):
    """In-session password change form requiring existing password confirmation."""

    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Current password"}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", "New passwords do not match.")
            else:
                validate_password(new_password)

        return cleaned_data

