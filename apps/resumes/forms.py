"""
Forms for Resume uploading and document version replacement.
"""
from django import forms
from .models import Resume
from .validators import validate_resume_file


class ResumeUploadForm(forms.ModelForm):
    """Candidate form for uploading a new resume in PDF or DOCX format."""

    file = forms.FileField(
        label="Resume Document (PDF or DOCX, max 10MB)",
        validators=[validate_resume_file],
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.docx"}),
    )

    class Meta:
        model = Resume
        fields = ["file", "is_primary"]
        widgets = {
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ResumeReplaceForm(forms.Form):
    """Candidate form for uploading a revised resume version."""

    file = forms.FileField(
        label="Select Revised Resume Document (.pdf or .docx)",
        validators=[validate_resume_file],
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.docx"}),
    )

