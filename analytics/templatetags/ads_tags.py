from django import template
from django.core.cache import cache
from django.utils.safestring import mark_safe

register = template.Library()

PROMO_AD_CACHE_KEY = 'analytics_promo_ad_html_v1'
PROMO_AD_CACHE_TTL = 60


@register.simple_tag
def get_custom_promo_ad():
    """Returns the staff-edited promo ad HTML (marked safe), or '' to fall
    back to the hardcoded default. Cached briefly since this renders on
    every homepage/create-tournament view."""
    cached = cache.get(PROMO_AD_CACHE_KEY)
    if cached is not None:
        return mark_safe(cached) if cached else ''

    from analytics.models import PromoAd
    row = PromoAd.objects.filter(pk=1, is_active=True).exclude(html_content='').first()
    html = row.html_content if row else ''
    cache.set(PROMO_AD_CACHE_KEY, html, PROMO_AD_CACHE_TTL)
    return mark_safe(html) if html else ''
