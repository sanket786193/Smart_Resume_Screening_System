"""
Constants and Choices for the Jobs application.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class JobType(models.TextChoices):
    FULL_TIME = "FULL_TIME", _("Full-Time")
    PART_TIME = "PART_TIME", _("Part-Time")
    CONTRACT = "CONTRACT", _("Contract")
    INTERNSHIP = "INTERNSHIP", _("Internship")
    FREELANCE = "FREELANCE", _("Freelance")


class WorkplaceType(models.TextChoices):
    ON_SITE = "ON_SITE", _("On-Site")
    HYBRID = "HYBRID", _("Hybrid")
    REMOTE = "REMOTE", _("Remote")


class JobStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    ACTIVE = "ACTIVE", _("Active (Accepting Applications)")
    CLOSED = "CLOSED", _("Closed")
    ARCHIVED = "ARCHIVED", _("Archived")


class EducationLevel(models.TextChoices):
    ANY = "ANY", _("Any / No Degree Required")
    HIGH_SCHOOL = "HIGH_SCHOOL", _("High School Diploma")
    ASSOCIATE = "ASSOCIATE", _("Associate Degree")
    BACHELOR = "BACHELOR", _("Bachelor's Degree")
    MASTER = "MASTER", _("Master's Degree")
    DOCTORATE = "DOCTORATE", _("Doctorate (PhD)")


DEFAULT_CURRENCY = "USD"
CURRENCY_CHOICES = [
    ("USD", "$ USD"),
    ("EUR", "€ EUR"),
    ("GBP", "£ GBP"),
    ("INR", "₹ INR"),
    ("CAD", "$ CAD"),
]

DEFAULT_PAGE_SIZE = 12
MAX_EXPERIENCE_YEARS = 40

