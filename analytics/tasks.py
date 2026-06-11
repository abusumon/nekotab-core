"""Celery tasks for analytics — offloads buffer flushes and ActiveSession writes
so the HTTP thread never waits on a DB round-trip.

PageView events are written to a Redis list by the middleware and bulk-read
here by flush_analytics_buffer, which pops batches of up to 1000 events and
bulk_inserts them into the PageView table.  This keeps the HTTP path fast,
survives worker restarts, and caps Redis memory with an LRU list.
"""

import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

ACTIVE_SESSION_STALE_SECONDS = 60 * 5  # 5 minutes
FLUSH_BATCH_SIZE = 1000           # number of events to pop per flush
REDIS_LIST_KEY = 'analytics:raw'  # must match middleware.REDIS_LIST_KEY

REDIS_LIST_MAX = 10_000   # hard cap: LTRIM drops oldest entries beyond this
REDIS_SAMPLE_THRESHOLD = 8_000   # start reservoir sampling above this depth
REDIS_SAMPLE_RATE = 5     # keep 1 in N beacons under high load


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
    max_retries=3,
    retry_backoff=True,
)
def flush_analytics_buffer():
    """Pop up to FLUSH_BATCH_SIZE events from the Redis analytics queue
    and bulk-insert them into the PageView table.

    RPOP is used so each event is consumed exactly once.  If the DB bulk
    insert succeeds, the events are already removed from Redis; if it
    fails the task is retried and the remaining events (not yet popped)
    are still safe in the Redis list.

    Also runs ActiveSession cleanup to keep the table small.
    """
    from django_redis import get_redis_connection
    from .models import ActiveSession, PageView

    redis_conn = get_redis_connection("default")

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
    # Fields allowed on PageView to prevent ** explosion from beacon events
    _allowed = {
        'path', 'full_url', 'session_key', 'ip_address', 'user_agent',
        'referer', 'device_type', 'browser', 'os', 'org_slug',
    }
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

        # Normalise beacon key difference: 'referrer' → 'referer'
        if 'referrer' in data and 'referer' not in data:
            data['referer'] = data.pop('referrer')

        # Strip unknown keys so PageView(**data) never raises TypeError
        data.pop('source', None)
        safe_data = {k: v for k, v in data.items() if k in _allowed}

        page_views.append(PageView(
            user=user,
            timestamp=timestamp,
            **safe_data,
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
    """Remove expired ActiveSession rows."""
    from .models import ActiveSession
    count = ActiveSession.cleanup_stale()
    logger.info("Analytics: removed %d stale sessions.", count)
    return count


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    name='analytics.tasks.aggregate_analytics_hourly',
)
def aggregate_analytics_hourly():
    """Upsert hourly per-org analytics aggregates from the last hour's PageView rows.

    Idempotent: running twice for the same hour-slot updates the same row
    (update_or_create) so counts do not double.  The task is designed to run
    at the top of every hour via Celery Beat.
    """
    import datetime

    from django.db.models import Count
    from django.utils import timezone as tz

    from .models import OrgAnalyticsSummary, PageView

    now = tz.now()
    # Align to the start of the *current* hour so running at 14:03 covers 13:00–14:00.
    window_end = now.replace(minute=0, second=0, microsecond=0)
    window_start = window_end - datetime.timedelta(hours=1)
    target_date = window_start.date()
    target_hour = window_start.hour

    # Aggregate by org_slug and path for the last completed hour.
    rows = (
        PageView.objects
        .filter(timestamp__gte=window_start, timestamp__lt=window_end)
        .exclude(org_slug='')
        .values('org_slug', 'path')
        .annotate(count=Count('id'))
    )

    # Gather (org_slug → {paths: [...], total: int}) map
    org_data: dict = {}
    for row in rows:
        slug = row['org_slug']
        entry = org_data.setdefault(slug, {'total': 0, 'paths': set()})
        entry['total'] += row['count']
        entry['paths'].add(row['path'])

    processed = 0
    for slug, data in org_data.items():
        existing = OrgAnalyticsSummary.objects.filter(
            org_slug=slug, date=target_date, hour=target_hour,
        ).first()

        new_views = data['total']
        new_paths = sorted(data['paths'])

        if existing:
            # Idempotent merge: replace counts with this run's values (task may
            # be retried; do not accumulate the same hour twice).
            merged_paths = sorted(set(existing.unique_paths) | set(new_paths))
            OrgAnalyticsSummary.objects.filter(pk=existing.pk).update(
                page_views=new_views,
                unique_paths=merged_paths,
            )
        else:
            OrgAnalyticsSummary.objects.create(
                org_slug=slug,
                date=target_date,
                hour=target_hour,
                page_views=new_views,
                unique_paths=new_paths,
            )
        processed += 1

    logger.info(
        'aggregate_analytics_hourly: %s–%s UTC → %d orgs processed.',
        window_start.strftime('%Y-%m-%d %H:%M'),
        window_end.strftime('%H:%M'),
        processed,
    )
    return processed


@shared_task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
)
def populate_daily_stats(days=1):
    """Aggregate raw PageView rows into DailyStats for the past *days* days.

    Mirrors the management command populate_daily_stats so that Celery Beat
    can schedule this task nightly at 00:05 UTC.
    """
    from datetime import date, timedelta

    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q
    from django.utils import timezone

    from .models import DailyStats, PageView

    User = get_user_model()
    today = timezone.localdate()
    target_dates = [today - timedelta(days=i + 1) for i in range(days)]

    populated = 0
    for target_date in target_dates:
        start = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        end = start + timedelta(days=1)

        # Use .only() to avoid SELECT * — we only need a handful of columns
        page_views = PageView.objects.filter(
            timestamp__gte=start, timestamp__lt=end,
        ).only('id', 'path', 'session_key', 'country', 'user_id')

        total_views     = page_views.count()
        unique_visitors = page_views.values('session_key').distinct().count()

        top_pages = {
            row['path']: row['count']
            for row in (
                page_views.values('path')
                .annotate(count=Count('id'))
                .order_by('-count')[:20]
            )
        }
        top_countries = {
            row['country']: row['count']
            for row in (
                page_views.exclude(country='')
                .values('country')
                .annotate(count=Count('id'))
                .order_by('-count')[:20]
            )
        }

        new_signups  = User.objects.filter(date_joined__gte=start, date_joined__lt=end).count()
        active_users = page_views.exclude(user=None).values('user').distinct().count()

        tournaments_created = 0
        active_tournaments  = 0
        try:
            from tournaments.models import Tournament
            tournaments_created = Tournament.objects.filter(created__gte=start, created__lt=end).count()
            active_tournaments  = Tournament.objects.filter(active=True).count()
        except Exception:
            pass

        debates_created = 0
        ballots_entered = 0
        try:
            from draw.models import Debate
            debates_created = Debate.objects.filter(
                round__starts_at__gte=start, round__starts_at__lt=end
            ).count()
        except Exception:
            pass
        try:
            from results.models import BallotSubmission
            ballots_entered = BallotSubmission.objects.filter(
                timestamp__gte=start, timestamp__lt=end
            ).count()
        except Exception:
            pass

        DailyStats.objects.update_or_create(
            date=target_date,
            defaults={
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'new_signups': new_signups,
                'active_users': active_users,
                'tournaments_created': tournaments_created,
                'active_tournaments': active_tournaments,
                'debates_created': debates_created,
                'ballots_entered': ballots_entered,
                'top_pages': top_pages,
                'top_countries': top_countries,
            },
        )
        populated += 1
        logger.info('DailyStats populated for %s: %d views, %d unique', target_date, total_views, unique_visitors)

    return populated
