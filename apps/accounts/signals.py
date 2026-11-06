"""
Signals for user lifecycle tracking.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def log_user_post_save(sender, instance, created, **kwargs):
    """Logs lifecycle creation events for auditing."""
    if created:
        logger.info(f"New user registered: {instance.username} ({instance.role})")

