"""Management command to populate DailyStats from raw PageView data.

Usage:
    python manage.py populate_daily_stats              # yesterday
    python manage.py populate_daily_stats --date 2025-01-15
    python manage.py populate_daily_stats --days 7     # last 7 days

Designed to run nightly via cron / Heroku Scheduler / Render Cron.
"""

import logging
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone

from analytics.models import DailyStats, PageView

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Aggregate raw PageView rows into DailyStats for one or more days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Specific date to populate (YYYY-MM-DD). Defaults to yesterday.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of past days to populate (starting from yesterday).",
        )

    def handle(self, *args, **options):
        if options["date"]:
            target_dates = [date.fromisoformat(options["date"])]
        else:
            today = timezone.localdate()
            target_dates = [today - timedelta(days=i + 1) for i in range(options["days"])]

        for d in target_dates:
            self._populate_date(d)

        self.stdout.write(self.style.SUCCESS(f"Populated DailyStats for {len(target_dates)} day(s)."))

    def _populate_date(self, target_date):
        start = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        end = start + timedelta(days=1)

        page_views = PageView.objects.filter(timestamp__gte=start, timestamp__lt=end)

        total_views = page_views.count()
        unique_visitors = page_views.values("session_key").distinct().count()

        # Top pages
        top_pages_qs = (
            page_views.values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )
        top_pages = {row["path"]: row["count"] for row in top_pages_qs}

        # Top countries
        top_countries_qs = (
            page_views.exclude(country="")
            .values("country")
            .annotate(count=Count("id"))
            .order_by("-count")[:20]
        )
        top_countries = {row["country"]: row["count"] for row in top_countries_qs}

        # New signups
        new_signups = User.objects.filter(
            date_joined__gte=start, date_joined__lt=end
        ).count()

        # Active users (users who made at least one page view)
        active_users = (
            page_views.exclude(user=None)
            .values("user")
            .distinct()
            .count()
        )

        # Tournaments created
        tournaments_created = 0
        active_tournaments = 0
        try:
            from tournaments.models import Tournament
            tournaments_created = Tournament.objects.filter(
                Q(created__gte=start) & Q(created__lt=end)
            ).count()
            active_tournaments = Tournament.objects.filter(active=True).count()
        except Exception:
            pass  # tournaments app may not be installed

        # Debates & ballots
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

        obj, created = DailyStats.objects.update_or_create(
            date=target_date,
            defaults={
                "total_views": total_views,
                "unique_visitors": unique_visitors,
                "new_signups": new_signups,
                "active_users": active_users,
                "tournaments_created": tournaments_created,
                "active_tournaments": active_tournaments,
                "debates_created": debates_created,
                "ballots_entered": ballots_entered,
                "top_pages": top_pages,
                "top_countries": top_countries,
            },
        )
        verb = "Created" if created else "Updated"
        logger.info("%s DailyStats for %s: %d views, %d unique", verb, target_date, total_views, unique_visitors)
        self.stdout.write(f"  {verb} stats for {target_date}: {total_views} views, {unique_visitors} unique visitors")
