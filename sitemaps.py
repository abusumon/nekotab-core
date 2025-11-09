from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from tournaments.models import Tournament


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return [
            'tabbycat-index',
            'tournament-create',
            'load-demo',
            'blank-site-start',
        ]

    def location(self, item):
        return reverse(item)


class TournamentSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Tournament.objects.filter(active=True)

    def location(self, obj):
        # Canonical path for tournament home under slug routing
        return f"/{obj.slug}/"

    def lastmod(self, obj):
        # Use updated field if present; else None
        return getattr(obj, 'updated_at', None)
