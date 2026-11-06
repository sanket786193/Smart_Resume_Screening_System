"""
Signals for the Jobs application.
Tracks lifecycle changes and dispatches audit events.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Job
from .constants import JobStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Job)
def handle_job_status_change(sender, instance, created, **kwargs):
    """Logs lifecycle changes when a job is created or its status transitions."""
    if created:
        logger.info(f"[JOB CREATED] '{instance.title}' (ID: {instance.pk}) posted by {instance.recruiter.username}")
    else:
        logger.info(f"[JOB UPDATED] '{instance.title}' (Status: {instance.status}) by {instance.recruiter.username}")

