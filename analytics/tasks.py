"""Celery tasks for analytics — offloads buffer flushes and ActiveSession writes
so the HTTP thread never waits on a DB round-trip."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

ACTIVE_SESSION_STALE_SECONDS = 60 * 5  # 5 minutes


@shared_task(
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
)
def touch_active_session(session_key, user_id=None, ip_address=None, current_path=None):
    """Create or refresh an ActiveSession record.

    This is deliberately a Celery task rather than an inline DB write so that
    a slow database connection doesn't add latency to every page view.
    """
    from .models import ActiveSession  # local import avoids early app-load

    user = None
    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.only('pk').get(pk=user_id)
        except User.DoesNotExist:
            pass

    ActiveSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'ip_address': ip_address,
            'current_path': current_path,
        },
    )


@shared_task(
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
)
def cleanup_stale_sessions():
    """Remove expired ActiveSession rows."""
    from .models import ActiveSession
    count = ActiveSession.cleanup_stale()
    logger.info("Analytics: removed %d stale sessions.", count)
    return count