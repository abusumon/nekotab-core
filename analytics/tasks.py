"\"\"\"Celery tasks for analytics — offloads buffer flushes and ActiveSession writes
so the HTTP thread never waits on a DB round-trip.

PageView events are written to a Redis list by the middleware and bulk-read
here by flush_analytics_buffer, which pops batches of up to 1000 events and
bulk_inserts them into the PageView table.  This keeps the HTTP path fast,
survives worker restarts, and caps Redis memory with an LRU list.
\"\"\"

import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

ACTIVE_SESSION_STALE_SECONDS = 60 * 5  # 5 minutes
FLUSH_BATCH_SIZE = 1000           # number of events to pop per flush
REDIS_LIST_KEY = 'analytics:raw'  # must match middleware.REDIS_LIST_KEY


@shared_task(
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
)
def touch_active_session(session_key, user_id=None, ip_address=None, current_path=None):
    \"\"\"Create or refresh an ActiveSession record.

    This is deliberately a Celery task rather than an inline DB write so that
    a slow database connection doesn't add latency to every page view.
    \"\"\"
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
    max_retries=3,
    retry_backoff=True,
)
def flush_analytics_buffer():
    \"\"\"Pop up to FLUSH_BATCH_SIZE events from the Redis analytics queue
    and bulk-insert them into the PageView table.

    RPOP is used so each event is consumed exactly once.  If the DB bulk
    insert succeeds, the events are already removed from Redis; if it
    fails the task is retried and the remaining events (not yet popped)
    are still safe in the Redis list.

    Also runs ActiveSession cleanup to keep the table small.
    \"\"\"
    from django_redis import get_redis_connection
    from .models import ActiveSession, PageView

    redis_conn = get_redis_connection(\"default\")

    # 1. Pop events from the Redis tail (oldest first, FIFO)
    raw_events = []
    for _ in range(FLUSH_BATCH_SIZE):
        item = redis_conn.rpop(REDIS_LIST_KEY)
        if item is None:
            break
        raw_events.append(item)

    if not raw_events:
        logger.debug('Analytics flush: Redis queue is empty.')
        return 0

    # 2. Deserialize and build PageView model instances
    page_views = []
    now = timezone.now()
    for raw in raw_events:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning('Analytics flush: could not decode JSON event.', exc_info=True)
            continue

        # Resolve user if user_id is present
        user = None
        user_id = data.pop('user_id', None)
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.only('pk').get(pk=user_id)
            except User.DoesNotExist:
                pass

        # Parse timestamp from ISO string
        timestamp = data.pop('timestamp', now.isoformat())
        try:
            from dateutil.parser import isoparse
            timestamp = isoparse(timestamp)
        except Exception:
            timestamp = now

        page_views.append(PageView(
            user=user,
            timestamp=timestamp,
            **data,
        ))

    # 3. Bulk insert (ignore_conflicts in case of rare duplicates)
    if page_views:
        try:
            PageView.objects.bulk_create(page_views, ignore_conflicts=True)
        except Exception:
            # Re-queue the raw events at the head of the list so they
            # are retried next time instead of being lost.
            for raw in reversed(raw_events):
                redis_conn.rpush(REDIS_LIST_KEY, raw)
            raise

    # 4. Cleanup stale ActiveSessions inline (cheap, no extra task needed)
    deleted = 0
    try:
        deleted = ActiveSession.cleanup_stale()
    except Exception:
        logger.warning('Analytics flush: ActiveSession cleanup failed.', exc_info=True)

    logger.info(
        'Analytics flush: inserted %d page views; removed %d stale sessions.',
        len(page_views), deleted,
    )
    return len(page_views)


@shared_task(
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
)
def cleanup_stale_sessions():
    \"\"\"Remove expired ActiveSession rows.\"\"\"
    from .models import ActiveSession
    count = ActiveSession.cleanup_stale()
    logger.info(\"Analytics: removed %d stale sessions.\", count)
    return count"
