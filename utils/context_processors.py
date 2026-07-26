import logging
import re

from django.conf import settings
from django.core.cache import cache

from tournaments.models import Tournament

logger = logging.getLogger(__name__)


# ── Ad placement path rules ──────────────────────────────────────────────
#
# Compiled once at import. ``_ANCHOR_ONLY_RE`` marks pages that get the
# sticky anchor but no in-content units; ``_ADS_OFF_RE`` marks pages with no
# ads at all. Both are matched with ``search`` against ``request.path`` so
# subdomain-served tournaments (internally prefixed with ``/<slug>/``) hit the
# same rules as path-served ones.

def _compile_path_rules(setting_name):
    patterns = getattr(settings, setting_name, ()) or ()
    if not patterns:
        return None
    return re.compile('|'.join('(?:%s)' % p for p in patterns))


_ANCHOR_ONLY_RE = _compile_path_rules('ADS_ANCHOR_ONLY_PATHS')
_ADS_OFF_RE = _compile_path_rules('ADS_DISABLED_PATHS')


def _premium_context(request, tournament):
    """Premium status of the tournament this request is about.

    Drives the upgrade prompts in the admin chrome. Returns the unlocked shape
    on any failure — a broken monetisation lookup must never take a page down,
    and showing no prompt is a much cheaper mistake than nagging a director who
    has already paid.
    """
    unlocked = {
        'tournament_is_premium': True,
        'premium_reason': 'disabled',
        'premium_purchase_url': '',
        'premium_trial_days_left': None,
    }

    tournament_pk = getattr(tournament, 'pk', None)
    if not tournament_pk:
        return unlocked

    try:
        from donations.premium import premium_page_url, premium_state
    except ImportError:
        # `donations` is a NekoTab-only app; upstream Tabbycat runs without it.
        return unlocked

    try:
        state = premium_state(tournament)
    except Exception:
        logger.exception('Premium lookup failed; treating the tournament as unlocked')
        return unlocked

    return {
        'tournament_is_premium': state['is_premium'],
        'premium_reason': state['reason'],
        # Present during a trial as well as when locked: the whole point of a
        # trial is that the director can pay before it runs out.
        'premium_purchase_url': (
            '' if state['reason'] in ('paid', 'grandfathered', 'disabled')
            else premium_page_url(tournament_pk)),
        'premium_trial_days_left': state['trial_days_left'],
    }


def _ad_context(request, tournament):
    """Ad placement flags for this request.

    Ads were switched off site-wide at the premium launch, so in normal
    operation this returns the all-off shape on the first branch. The path
    rules below still work and still matter if ``ADSENSE_ENABLED`` is ever
    turned back on.
    """
    off = {'ads_enabled': False, 'ads_anchor_only': False, 'ads_removal_url': ''}

    if not getattr(settings, 'ADSENSE_ENABLED', False):
        return off

    # A tournament that has been paid for never shows ads, whatever the
    # site-wide switch says.
    if _premium_context(request, tournament)['premium_reason'] == 'paid':
        return off

    path = getattr(request, 'path', '') or '/'
    if _ADS_OFF_RE is not None and _ADS_OFF_RE.search(path):
        return off

    return dict(
        off,
        ads_enabled=True,
        ads_anchor_only=bool(_ANCHOR_ONLY_RE is not None and _ANCHOR_ONLY_RE.search(path)),
    )

COUNTRY_HEADER_KEYS = (
    'HTTP_CF_IPCOUNTRY',
    'HTTP_CLOUDFRONT_VIEWER_COUNTRY',
    'HTTP_X_COUNTRY_CODE',
    'HTTP_X_APPENGINE_COUNTRY',
    'GEOIP_COUNTRY_CODE',
)

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


def _get_request_country_code(request):
    """Return a normalized ISO-3166 country code from trusted proxy headers."""
    meta = getattr(request, 'META', {}) or {}

    for header in COUNTRY_HEADER_KEYS:
        value = meta.get(header)
        if not value:
            continue
        code = str(value).strip().upper()
        if len(code) == 2 and code.isalpha():
            return code

    return ''


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
        # AdSense — `ads_enabled` (computed below) is the flag templates should
        # gate on; `adsense_enabled` is the raw site-wide switch.
        'adsense_enabled': getattr(settings, 'ADSENSE_ENABLED', False),
        'adsense_publisher_id': getattr(settings, 'ADSENSE_PUBLISHER_ID', ''),
        'adsense_slot_content': getattr(settings, 'ADSENSE_SLOT_CONTENT', ''),
        'adsense_slot_footer': getattr(settings, 'ADSENSE_SLOT_FOOTER', ''),
        'adsense_slot_table': getattr(settings, 'ADSENSE_SLOT_TABLE', ''),
        'adsense_slot_anchor': getattr(settings, 'ADSENSE_SLOT_ANCHOR', ''),
        'ads_price_label': getattr(settings, 'PREMIUM_PRICE_LABEL', '$5'),
        'premium_price_label': getattr(settings, 'PREMIUM_PRICE_LABEL', '$5'),
        'premium_enabled': getattr(settings, 'PREMIUM_ENABLED', False),
        # SEO defaults
        'seo_site_name': 'NekoTab Debate Tabulation',
        'seo_keywords': 'debate tab, debate tabulation, debate motion bank, BP motions, british parliamentary debate, WSDC motions, parliamentary debating, adjudicator allocation, debate tournament software, asian parliamentary, australs debating, debate results live, debate ticketing, debate schedule planner, debate registration forms, debate website builder, nekotab, free debate tab software',
        'seo_base_url': getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app'),
        'request_country_code': _get_request_country_code(request),
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

    # Both must run after `tournament` is resolved above — premium is granted
    # per-tournament.
    context.update(_premium_context(request, context.get('tournament')))
    context.update(_ad_context(request, context.get('tournament')))

    return context
