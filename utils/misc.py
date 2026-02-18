import logging
from secrets import SystemRandom
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.shortcuts import redirect
from django.urls import reverse
from django.utils import formats, timezone, translation
from ipware import get_client_ip

logger = logging.getLogger(__name__)


def _subdomain_settings():
    """Return (enabled, base_domain) for subdomain routing."""
    from django.conf import settings
    enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
    return enabled, base_domain


def _to_subdomain_url(slug, path):
    """Convert a path-based tournament URL to a full subdomain URL.
    Strips the /<slug>/ prefix from the path and prepends the subdomain host.
    Always uses HTTPS (production subdomains require it)."""
    slug_prefix = f'/{slug}/'
    if path.startswith(slug_prefix):
        path = '/' + path[len(slug_prefix):]
    return f'https://{slug}.{_subdomain_settings()[1]}{path}'


def get_ip_address(request):
    client_ip, is_routable = get_client_ip(request)
    if client_ip is None:
        return "0.0.0.0"
    return client_ip


def redirect_tournament(to, tournament, *args, **kwargs):
    """Redirect to a tournament view. When subdomain routing is enabled,
    redirects directly to the subdomain URL (e.g. https://slug.nekotab.app/...)."""
    enabled, base_domain = _subdomain_settings()
    if enabled and base_domain:
        reverse_kwargs = {k: v for k, v in kwargs.items() if k != 'permanent'}
        reverse_kwargs['tournament_slug'] = tournament.slug
        path = reverse(to, args=args, kwargs=reverse_kwargs)
        return redirect(_to_subdomain_url(tournament.slug, path))
    return redirect(to, tournament_slug=tournament.slug, *args, **kwargs)


def reverse_tournament(to, tournament, *args, **kwargs):
    kwargs.setdefault('kwargs', {})
    kwargs['kwargs']['tournament_slug'] = tournament.slug
    return reverse(to, *args, **kwargs)


def subdomain_reverse_tournament(to, tournament, *args, **kwargs):
    """Like reverse_tournament but returns a full subdomain URL when enabled.
    Falls back to the normal path when subdomain routing is disabled."""
    path = reverse_tournament(to, tournament, *args, **kwargs)
    enabled, base_domain = _subdomain_settings()
    if enabled and base_domain:
        return _to_subdomain_url(tournament.slug, path)
    return path


def redirect_round(to, round, *args, **kwargs):
    """Redirect to a round view. When subdomain routing is enabled,
    redirects directly to the subdomain URL."""
    enabled, base_domain = _subdomain_settings()
    if enabled and base_domain:
        reverse_kwargs = {k: v for k, v in kwargs.items() if k != 'permanent'}
        reverse_kwargs['tournament_slug'] = round.tournament.slug
        reverse_kwargs['round_seq'] = round.seq
        path = reverse(to, args=args, kwargs=reverse_kwargs)
        return redirect(_to_subdomain_url(round.tournament.slug, path))
    return redirect(to, tournament_slug=round.tournament.slug,
                    round_seq=round.seq, *args, **kwargs)


def reverse_round(to, round, *args, **kwargs):
    kwargs.setdefault('kwargs', {})
    kwargs['kwargs']['tournament_slug'] = round.tournament.slug
    kwargs['kwargs']['round_seq'] = round.seq
    return reverse(to, *args, **kwargs)


def subdomain_reverse_round(to, round, *args, **kwargs):
    """Like reverse_round but returns a full subdomain URL when enabled."""
    path = reverse_round(to, round, *args, **kwargs)
    enabled, base_domain = _subdomain_settings()
    if enabled and base_domain:
        return _to_subdomain_url(round.tournament.slug, path)
    return path


def badge_datetime_format(timestamp):
    lang = translation.get_language()
    for module in formats.get_format_modules(lang):
        fmt = getattr(module, "BADGE_DATETIME_FORMAT", None)
        if fmt is not None:
            break
    else:
        logger.error("No BADGE_DATETIME_FORMAT found for language: %s", lang)
        fmt = "d/m H:i"   # 18/02 16:33, as fallback in case nothing is defined

    localized_time = timezone.localtime(timestamp)
    return formats.date_format(localized_time, format=fmt)


def ranks_dictionary(tournament, score_min, score_max):
    """ Used for both adjudicator ranks and venue priorities """
    score_range = score_max - score_min
    return [
        {'pk': 'a+', 'fields': {'name': 'A+', 'cutoff': (score_range * 0.9) + score_min}},
        {'pk': 'a',  'fields': {'name': 'A', 'cutoff': (score_range * 0.8) + score_min}},
        {'pk': 'a-', 'fields': {'name': 'A-', 'cutoff': (score_range * 0.7) + score_min}},
        {'pk': 'b+', 'fields': {'name': 'B+', 'cutoff': (score_range * 0.6) + score_min}},
        {'pk': 'b',  'fields': {'name': 'B', 'cutoff': (score_range * 0.5) + score_min}},
        {'pk': 'b-', 'fields': {'name': 'B-', 'cutoff': (score_range * 0.4) + score_min}},
        {'pk': 'c+', 'fields': {'name': 'C+', 'cutoff': (score_range * 0.3) + score_min}},
        {'pk': 'c',  'fields': {'name': 'C', 'cutoff': (score_range * 0.2) + score_min}},
        {'pk': 'f',  'fields': {'name': 'F', 'cutoff': score_min}},
    ]


def generate_identifier_string(charset, length):
    """Used in privateurl/checkin identifier generation"""
    return ''.join(SystemRandom().choice(charset) for _ in range(length))


def add_query_string_parameter(url, key, value):
    scheme, netloc, path, params, query, fragment = urlparse(url)
    query_parts = parse_qs(query)
    query_parts[key] = value
    query = urlencode(query_parts, safe='/')
    return urlunparse((scheme, netloc, path, params, query, fragment))


def build_tournament_absolute_uri(request, tournament, path=None):
    """Build a full absolute URL for a tournament page, subdomain-aware.

    When subdomain routing is enabled, returns e.g.
        https://slug.nekotab.app/motions/
    When disabled, falls back to request.build_absolute_uri(path), e.g.
        https://nekotab.app/slug/motions/

    ``path`` should be the result of reverse_tournament() or any path that
    starts with /<slug>/.  If *path* is None the tournament root is used.

    The function strips a leading /<slug>/ prefix from *path* when building
    the subdomain form so callers never have to worry about double-slugs.
    """
    from django.conf import settings

    slug = tournament.slug
    if path is None:
        path = f'/{slug}/'

    subdomain_enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')

    if subdomain_enabled and base_domain:
        return _to_subdomain_url(slug, path)
    else:
        return request.build_absolute_uri(path)
