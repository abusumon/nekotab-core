import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PageView(models.Model):
    """Track individual page views for analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.CharField(max_length=500)
    full_url = models.URLField(max_length=1000, blank=True)
    
    # Visitor info
    session_key = models.CharField(max_length=100, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(max_length=1000, blank=True)
    
    # Location (from IP geolocation)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Device info
    device_type = models.CharField(max_length=20, blank=True)  # desktop, mobile, tablet
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # Org-specific tracking (set for beacon events from public org pages)
    org_slug = models.CharField(max_length=80, blank=True, default='', db_index=False)

    # Timing
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'path']),
            models.Index(fields=['session_key', 'timestamp']),
            # Composite index for per-org time-range queries (beacon analytics)
            models.Index(fields=['org_slug', 'timestamp'], name='analytics_pv_org_slug_ts_idx'),
            # Standalone timestamp index for global time-range aggregations
            models.Index(fields=['timestamp'], name='analytics_pv_ts_idx'),
        ]
    
    def __str__(self):
        return f"{self.path} - {self.timestamp}"


class DailyStats(models.Model):
    """Aggregated daily statistics for faster querying."""
    
    date = models.DateField(unique=True, db_index=True)
    
    # Traffic
    total_views = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    
    # Users
    new_signups = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    
    # Tournaments
    tournaments_created = models.PositiveIntegerField(default=0)
    active_tournaments = models.PositiveIntegerField(default=0)
    
    # Debates
    debates_created = models.PositiveIntegerField(default=0)
    ballots_entered = models.PositiveIntegerField(default=0)
    
    # Top pages (JSON)
    top_pages = models.JSONField(default=dict, blank=True)
    
    # Top countries (JSON)
    top_countries = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Daily stats"
    
    def __str__(self):
        return f"Stats for {self.date}"


class OrgAnalyticsSummary(models.Model):
    """Hourly pre-aggregated page-view counts per organisation.

    Written by the `aggregate_analytics_hourly` Celery task every hour.
    The (org_slug, date, hour) triplet is the idempotent upsert key.
    Reading from this table instead of raw PageView rows keeps the analytics
    dashboard fast even when PageView has millions of rows.
    """

    org_slug = models.CharField(max_length=80, db_index=True, verbose_name=_("org slug"))
    date = models.DateField(db_index=True, verbose_name=_("date"))
    # 0-23 hour in UTC
    hour = models.SmallIntegerField(verbose_name=_("hour (UTC)"))
    page_views = models.PositiveIntegerField(default=0, verbose_name=_("page views"))
    # JSON list of unique path strings seen during this hour
    unique_paths = models.JSONField(default=list, blank=True, verbose_name=_("unique paths"))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_("last updated"))

    class Meta:
        verbose_name = _("org analytics summary")
        verbose_name_plural = _("org analytics summaries")
        constraints = [
            models.UniqueConstraint(
                fields=['org_slug', 'date', 'hour'],
                name='analytics_orgsum_org_date_hour_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=['org_slug', 'date'], name='analytics_orgsum_slug_date_idx'),
        ]
        ordering = ['-date', '-hour']

    def __str__(self):
        return f"{self.org_slug} {self.date} h{self.hour:02d}: {self.page_views} views"


class ActiveSession(models.Model):
    """Track currently active sessions for real-time visitor count."""
    
    session_key = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    current_path = models.CharField(max_length=500, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(auto_now_add=True)
    
    # Location
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session {self.session_key[:8]}..."
    
    @classmethod
    def cleanup_stale(cls):
        """Remove sessions inactive for more than 5 minutes."""
        cutoff = timezone.now() - timedelta(minutes=5)
        cls.objects.filter(last_activity__lt=cutoff).delete()
