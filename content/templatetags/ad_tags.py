from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('ads/ad_unit.html', takes_context=True)
def ad_unit(context, slot_id, ad_format='auto', layout=''):
    """Render a single AdSense ad unit.

    Usage:
        {% load ad_tags %}
        {% ad_unit "1234567890" %}
        {% ad_unit "1234567890" "horizontal" %}
        {% ad_unit "1234567890" "auto" "sidebar" %}

    The ad only renders when ADSENSE_ENABLED=True AND the current page
    is NOT an admin page (user_role != 'admin').
    """
    user_role = context.get('user_role', '')
    enabled = context.get('adsense_enabled', False)
    publisher_id = context.get('adsense_publisher_id', '')

    # Never show ads on admin/assistant pages
    if user_role in ('admin', 'assistant'):
        enabled = False

    return {
        'show': enabled and bool(publisher_id) and bool(slot_id),
        'publisher_id': publisher_id,
        'slot_id': slot_id,
        'ad_format': ad_format,
        'layout': layout,
    }
