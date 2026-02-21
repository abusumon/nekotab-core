from django.contrib.sitemaps import Sitemap
from .models import Article


class LearnArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Article.objects.filter(status=Article.Status.PUBLISHED)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class TrustPagesSitemap(Sitemap):
    """Static trust/legal pages that should always be indexed."""
    changefreq = "monthly"
    priority = 0.5

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
