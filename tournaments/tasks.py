"""Celery tasks for tournaments.

Picked up by ``app.autodiscover_tasks()`` in ``tabbycat/celery_config.py``,
which is why this module has to be named ``tasks.py`` and live at the app root
— same as ``analytics.tasks`` and ``organizations.tasks``.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='tournaments.tasks.cleanup_expired_demos')
def cleanup_expired_demos(limit=0):
    """Delete demo tournaments past their expiry.

    Thin wrapper over the management command so there is exactly one
    implementation of the deletion logic and the manual path is the same code
    the scheduler runs. Mirrors how the retention engine is fronted by
    ``purge_tournaments``.

    Errors are logged and swallowed rather than raised: a failure here should
    show up in the logs and be retried on the next tick, not mark the beat
    schedule unhealthy. Per-tournament failures are already isolated inside
    the command.
    """
    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    try:
        call_command('cleanup_expired_demos', limit=limit, stdout=out)
    except Exception:
        logger.exception('cleanup_expired_demos task failed')
        return ''

    summary = out.getvalue().strip()
    if summary:
        logger.info('cleanup_expired_demos: %s', summary.replace('\n', ' | '))
    return summary
