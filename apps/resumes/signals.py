"""
Signals for the Resumes application.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Resume

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Resume)
def handle_resume_post_save(sender, instance, created, **kwargs):
    """Logs lifecycle changes on resume upload and replacement."""
    if created:
        logger.info(f"[RESUME UPLOADED] ID {instance.pk} by {instance.candidate.username} (v{instance.version})")
    else:
        logger.info(f"[RESUME UPDATED] ID {instance.pk} status: {instance.parsing_status}")

