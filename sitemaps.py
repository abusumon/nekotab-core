from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from tournaments.models import Tournament


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"

    _priorities = {
        'tabbycat-index': 1.0,
        'motionbank:motion-doctor': 0.9,
        'motionbank:motionbank-home': 0.9,
        'forum:forum-home': 0.7,
        'passport:passport-directory': 0.6,
    }

    def items(self):
        # Only include pages with meaningful content — exclude utility/auth pages
        return [
            'tabbycat-index',
            'forum:forum-home',
            'motionbank:motionbank-home',
            'motionbank:motion-doctor',
            'passport:passport-directory',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self._priorities.get(item, 0.7)


class TournamentSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Tournament.objects.filter(active=True, is_listed=True)

    def location(self, obj):
        # When subdomain routing is enabled, sitemaps should still use
        # path-based URLs since the sitemap XML is served from the main domain.
        # Search engines will discover the subdomain via canonical tags.
        return f"/{obj.slug}/"

    def lastmod(self, obj):
        # Use updated field if present; else None
        return getattr(obj, 'updated_at', None)


class MotionBankSitemap(Sitemap):
    """Sitemap for individual motion pages — SEO goldmine."""
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        from motionbank.models import MotionEntry
        return MotionEntry.objects.filter(is_approved=True).order_by('-created_at')

    def location(self, obj):
        return f"/motions-bank/motion/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at
