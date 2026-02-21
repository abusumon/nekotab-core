from django.contrib.sitemaps import Sitemap
from .models import Article


class LearnArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Article.objects.filter(status=Article.Status.PUBLISHED)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class TrustPagesSitemap(Sitemap):
    """Static trust/legal pages that should always be indexed."""
    changefreq = "monthly"

    _priorities = {
        '/learn/': 0.8,
        '/about/': 0.5,
        '/contact/': 0.5,
        '/privacy/': 0.4,
        '/terms/': 0.4,
        '/disclaimer/': 0.4,
    }

    def items(self):
        return [
            ('content:about', '/about/'),
            ('content:contact', '/contact/'),
            ('content:privacy', '/privacy/'),
            ('content:terms', '/terms/'),
            ('content:disclaimer', '/disclaimer/'),
            ('content:learn-hub', '/learn/'),
        ]

    def location(self, item):
        return item[1]

    def priority(self, item):
        return self._priorities.get(item[1], 0.5)
