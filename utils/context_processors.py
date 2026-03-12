import logging

from django.conf import settings
from django.core.cache import cache

from tournaments.models import Tournament

logger = logging.getLogger(__name__)

# ── Navbar tournament cache ──────────────────────────────────────────────
#
# Per-user key incorporates the permission-cache version so that org-
# membership changes (which bump the version in organizations/signals.py)
# automatically invalidate the stale navbar list.
#
# Anonymous users share a single global key.
#
# Cache stores a list of NavTournament (lightweight, no ORM state).

NAV_CACHE_KEY = "nav_tournaments:u%d:v%d"
NAV_CACHE_KEY_ANON = "nav_tournaments:anon"
NAV_CACHE_TTL = 120  # seconds


class NavTournament:
    """Lightweight, cache-safe tournament representation for navbar rendering.

    Has the same attribute interface expected by the sidebar / top-nav
    templates (``slug``, ``name``, ``user_can_admin``, etc.) without ORM
    overhead or stale-state risks.
    """
    __slots__ = ('pk', 'slug', 'name', 'short_name',
                 'user_can_admin', 'user_can_assist', 'user_can_edit_db')

    def __init__(self, **kwargs):
        for key in self.__slots__:
            setattr(self, key, kwargs.get(key))

    def __str__(self):
        return self.short_name or self.name

    def __repr__(self):
        return f"NavTournament(slug={self.slug!r})"


def _get_nav_tournaments(user):
    """Return a list of :class:`NavTournament` for the current user.

    First request hits the DB (single query via ``nav_for_user``); the
    result is cached per-user with a versioned key so that membership
    changes invalidate it immediately.
    """
    from organizations.signals import get_perm_cache_version

    if user is None or not getattr(user, 'is_authenticated', False):
        cached = cache.get(NAV_CACHE_KEY_ANON)
        if cached is not None:
            return cached
        result = _evaluate_nav_qs(None)
        cache.set(NAV_CACHE_KEY_ANON, result, NAV_CACHE_TTL)
        return result

    version = get_perm_cache_version(user.pk)
    key = NAV_CACHE_KEY % (user.pk, version)
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = _evaluate_nav_qs(user)
    cache.set(key, result, NAV_CACHE_TTL)
    return result


def _evaluate_nav_qs(user):
    """Execute ``nav_for_user()`` and convert to a list of NavTournament."""
    return [
        NavTournament(
            pk=t.pk,
            slug=t.slug,
            name=t.name,
            short_name=t.short_name,
            user_can_admin=t.user_can_admin,
            user_can_assist=t.user_can_assist,
            user_can_edit_db=t.user_can_edit_db,
        )
        for t in Tournament.objects.nav_for_user(user)
    ]


def debate_context(request):

    subdomain_enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')

    user = getattr(request, 'user', None)

    nav_tournaments = _get_nav_tournaments(user)

    context = {
        'tabbycat_version': settings.TABBYCAT_VERSION or "",
        'tabbycat_codename': settings.TABBYCAT_CODENAME or "no codename",
        'all_tournaments': nav_tournaments,
        'user_can_edit_db': any(t.user_can_edit_db for t in nav_tournaments),
        'disable_sentry': getattr(settings, 'DISABLE_SENTRY', False),
        'on_local': getattr(settings, 'ON_LOCAL', False),
        'hmr': getattr(settings, 'USE_WEBPACK_SERVER', False),
        'subdomain_enabled': subdomain_enabled,
        'subdomain_base_domain': base_domain,
        # AdSense
        'adsense_enabled': getattr(settings, 'ADSENSE_ENABLED', False),
        'adsense_publisher_id': getattr(settings, 'ADSENSE_PUBLISHER_ID', ''),
        # SEO defaults
        'seo_site_name': 'NekoTab Debate Tabulation',
        'seo_keywords': 'debate tab, debate tabulation, parliamentary debating, BP motions, adjudicator allocation, debate tournament software, asian parliamentary, australs debating, british parliamentary, debate results live',
        'seo_base_url': getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app'),
    }

    # Canonical URL: use subdomain form when tournament is served via subdomain
    try:
        path = request.path if hasattr(request, 'path') else '/'
        subdomain_slug = getattr(request, 'subdomain_tournament', None)

        if subdomain_slug and subdomain_enabled and base_domain:
            # Strip the internally-prefixed /<slug>/ from path for canonical
            slug_prefix = f'/{subdomain_slug}/'
            if path.startswith(slug_prefix):
                clean_path = path[len(slug_prefix) - 1:]  # keep leading /
            else:
                clean_path = path
            context['canonical_url'] = f"https://{subdomain_slug}.{base_domain}{clean_path}"
        else:
            base = getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app').rstrip('/')
            context['canonical_url'] = f"{base}{path}"
    except Exception:
        context['canonical_url'] = None

    if hasattr(request, 'tournament'):
        current_round = request.tournament.current_round

        context.update({
            'tournament': request.tournament,
            'pref': request.tournament.preferences.by_name(),
            'current_round': current_round,
        })
        if hasattr(request, 'round'):
            context['round'] = request.round

    # Organization workspace context
    tenant_org = getattr(request, 'tenant_organization', None)
    if tenant_org:
        context['workspace_org'] = tenant_org
        context['workspace_url'] = f"https://{tenant_org.slug}.{base_domain}/"

    return context
