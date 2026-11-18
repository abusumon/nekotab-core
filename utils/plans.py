"""The one seam between open-source Tabbycat code and NekoTab's paid plans.

Core code asks two questions and never imports the private ``donations`` app
directly:

* :func:`plans_live` / :func:`new_features_visible` — has the 1 December launch
  happened (or is a superuser previewing it)?
* :func:`tournament_allows` — may this tournament use a plan feature, such as
  ``'email'`` or ``'release_to_teams'``?

Without the donations app (a self-hosted copy of the public code) every answer
is "yes": plans are a NekoTab hosting decision, not a Tabbycat one. Every
lookup also fails open, because wrongly blocking a director mid-round costs far
more than wrongly letting one feature through.
"""
import datetime
import logging

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


def launch_at():
    raw = getattr(settings, 'PLANS_LAUNCH_AT', '') or ''
    value = parse_datetime(raw) if isinstance(raw, str) else raw
    if value is None:
        return datetime.datetime(2026, 12, 1, tzinfo=datetime.timezone(datetime.timedelta(hours=6)))
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value


def plans_live(now=None):
    return (now or timezone.now()) >= launch_at()


def new_features_visible(request):
    """New plan-era features show to everyone after launch, and to superusers before it."""
    if plans_live():
        return True
    user = getattr(request, 'user', None)
    return bool(user is not None and user.is_authenticated and user.is_superuser)


def tournament_allows(tournament, feature):
    try:
        from donations.plans import tournament_allows as _allows
    except ImportError:
        return True
    try:
        return _allows(tournament, feature)
    except Exception:
        logger.exception('Plan check failed for %s on tournament %r; allowing', feature, getattr(tournament, 'pk', None))
        return True


def upgrade_url(tournament):
    try:
        from donations.premium import premium_page_url
        return premium_page_url(tournament.pk)
    except Exception:
        return ''
