"""
Forms for Job creation, updating, searching, and faceted filtering.
"""
from django import forms
from django.utils import timezone
from .models import Job
from .constants import (
    JobType,
    WorkplaceType,
    EducationLevel,
    JobStatus,
)
from .validators import validate_salary_range, validate_experience_range


class JobCreateUpdateForm(forms.ModelForm):
    """Recruiter form for publishing or amending job postings."""

    skills_input = forms.CharField(
        label="Required & Preferred Skills",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Python, Django, PostgreSQL, Docker, AWS, REST API",
            }
        ),
        help_text="Enter skills separated by commas. Our AI parser extracts and standardizes them.",
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "department",
            "job_type",
            "workplace_type",
            "location",
            "experience_min",
            "experience_max",
            "education_level",
            "salary_min",
            "salary_max",
            "currency",
            "is_salary_negotiable",
            "deadline",
            "status",
            "description",
            "responsibilities",
            "requirements",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Senior Python / Django Developer"}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Software Engineering"}),
            "job_type": forms.Select(attrs={"class": "form-select"}),
            "workplace_type": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. New York, NY or Remote"}),
            "experience_min": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "experience_max": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "education_level": forms.Select(attrs={"class": "form-select"}),
            "salary_min": forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 90000"}),
            "salary_max": forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 130000"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "is_salary_negotiable": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "deadline": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "responsibilities": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "requirements": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")
        validate_salary_range(salary_min, salary_max)

        exp_min = cleaned_data.get("experience_min")
        exp_max = cleaned_data.get("experience_max")
        validate_experience_range(exp_min, exp_max)

        deadline = cleaned_data.get("deadline")
        if deadline and deadline <= timezone.now():
            self.add_error("deadline", "Deadline must be in the future.")

        return cleaned_data


class JobFilterForm(forms.Form):
    """Search and filter form for candidates browsing jobs."""

    SORT_CHOICES = [
        ("-created_at", "Newest First"),
        ("created_at", "Oldest First"),
        ("deadline", "Closing Soonest"),
        ("-salary_max", "Highest Salary"),
        ("experience_min", "Least Experience Required"),
    ]

    q = forms.CharField(
        required=False,
        label="Search Jobs",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search by title, skill, or keyword..."}
        ),
    )
    job_type = forms.ChoiceField(
        required=False,
        choices=[("", "-- All Job Types --")] + JobType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    workplace_type = forms.ChoiceField(
        required=False,
        choices=[("", "-- All Workplace Types --")] + WorkplaceType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    education_level = forms.ChoiceField(
        required=False,
        choices=[("", "-- All Education Levels --")] + EducationLevel.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City or Remote..."}),
    )
    max_experience = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Max Years"}),
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

