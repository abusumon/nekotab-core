import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseNotFound, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from tournaments.models import Round, Tournament


class DebateMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if 'tournament_slug' in view_kwargs and request.path.split('/')[1] != 'api':
            slug = view_kwargs['tournament_slug']

            # --- Redirect path-based access to subdomain ---
            # When subdomain routing is enabled and the request arrived on the
            # main domain (not already via a subdomain), 301-redirect GET/HEAD
            # requests to the canonical subdomain URL.
            subdomain_on = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
            base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
            already_subdomain = getattr(request, 'subdomain_tournament', None)

            if (subdomain_on and base_domain
                    and not already_subdomain
                    and request.method in ('GET', 'HEAD')):
                path = request.get_full_path()  # includes query string
                slug_prefix = f'/{slug}/'
                if path.startswith(slug_prefix):
                    clean_path = '/' + path[len(slug_prefix):]
                elif path == f'/{slug}':
                    clean_path = '/'
                else:
                    clean_path = path
                return HttpResponsePermanentRedirect(
                    f'https://{slug}.{base_domain}{clean_path}')

            # --- Cache tournament object ---
            cached_key = "%s_%s" % (slug, 'object')
            cached_tournament_object = cache.get(cached_key)

            if cached_tournament_object:
                request.tournament = cached_tournament_object
            else:
                request.tournament = get_object_or_404(
                    Tournament, slug=slug)
                cache.set(cached_key, request.tournament, None)

            if 'round_seq' in view_kwargs:
                cached_key = "%s_%s_%s" % (slug,
                                           view_kwargs['round_seq'], 'object')
                cached_round_object = cache.get(cached_key)
                if cached_round_object:
                    request.round = cached_round_object
                else:
                    request.round = get_object_or_404(
                        Round,
                        tournament=request.tournament,
                        seq=view_kwargs['round_seq'])
                    cache.set(cached_key, request.round, None)

        return None


def get_subdomain_url(tournament_slug, path='/', scheme='https'):
    """Build a full subdomain URL for a tournament.

    Args:
        tournament_slug: The tournament's slug (e.g. 'ndf-nationals-2025')
        path: The path portion (e.g. '/motions/')
        scheme: URL scheme, defaults to 'https'

    Returns:
        Full URL like 'https://ndf-nationals-2025.nekotab.app/motions/'
        or None if subdomain routing is disabled.
    """
    if not getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False):
        return None
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
    if not base_domain:
        return None
    if not path.startswith('/'):
        path = '/' + path
    return f"{scheme}://{tournament_slug}.{base_domain}{path}"


class SubdomainTournamentMiddleware(object):
    """
    Allows accessing tournaments using subdomains, e.g.
    https://ndf-nationals-2025.nekotab.app/motions/ will be internally
    rewritten so that Django sees the path as /ndf-nationals-2025/motions/

    When a subdomain is detected, the middleware:
    1. Prefixes request.path_info with /<slug>/ so Django's URL resolver
       matches the existing <slug:tournament_slug>/ URL patterns.
    2. Sets request.subdomain_tournament = slug so that templates and
       context processors can generate subdomain-aware canonical URLs.

    Enable by setting SUBDOMAIN_TOURNAMENTS_ENABLED=true and
    SUBDOMAIN_BASE_DOMAIN=nekotab.app (or your root domain).
    """

    RESERVED_SUBDOMAINS_DEFAULT = {
        'www', 'admin', 'api', 'static', 'media', 'jet', 'database'
    }

    # Paths that should never be rewritten (global routes)
    BAD_PREFIXES = (
        '/static/', '/media/', '/admin/', '/database/', '/api/',
        '/analytics/', '/accounts/', '/campaigns/', '/notifications/',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
        self.base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
        reserved = getattr(settings, 'RESERVED_SUBDOMAINS', None)
        if reserved is None:
            self.reserved = self.RESERVED_SUBDOMAINS_DEFAULT
        else:
            self.reserved = set(reserved)
        self.slug_re = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')

    def _extract_tournament_subdomain(self, request):
        """Extract tournament slug from the Host header subdomain.
        Returns the slug string, or None if not a tournament subdomain."""
        try:
            host = request.get_host().split(':')[0].lower()
        except Exception:
            return None

        if not host or not host.endswith(self.base_domain):
            return None

        # Strip base domain and trailing dot: "slug.nekotab.app" -> "slug"
        subpart = host[:-len(self.base_domain)].rstrip('.')
        if not subpart:
            return None

        # Only single-label subdomains (no nested like a.b.nekotab.app)
        if '.' in subpart:
            return None

        label = subpart
        if not label or label in self.reserved or not self.slug_re.match(label):
            return None

        return label

    def __call__(self, request):
        # Always initialize the flag
        request.subdomain_tournament = None

        if not self.enabled or not self.base_domain:
            return self.get_response(request)

        label = self._extract_tournament_subdomain(request)
        if not label:
            return self.get_response(request)

        # Verify this slug belongs to a real tournament (cached 5 min)
        cache_key = f"subdom_tour_exists_{label}"
        exists = cache.get(cache_key)
        if exists is None:
            exists = Tournament.objects.filter(slug=label).exists()
            cache.set(cache_key, exists, 300)

        if not exists:
            # Tournament subdomain doesn't exist — return a friendly 404
            try:
                html = render_to_string('errors/subdomain_404.html', {
                    'subdomain': label,
                    'base_domain': self.base_domain,
                })
                return HttpResponseNotFound(html)
            except Exception:
                return HttpResponseNotFound(
                    f'<h1>Tournament not found</h1>'
                    f'<p>No tournament exists at <strong>{label}.{self.base_domain}</strong>.</p>'
                    f'<p><a href="https://{self.base_domain}/">Go to NekoTab home</a></p>'
                )

        # Tag the request so context processors / templates know
        request.subdomain_tournament = label

        # Prefix the path so Django's URL resolver finds the right view,
        # but only if not already prefixed and not a global route
        if (not request.path_info.startswith(f'/{label}/')
                and not request.path_info.startswith(self.BAD_PREFIXES)):

            # Guard against double-prefixing: if the first path segment is
            # already another tournament's slug, don't prepend ours.
            first_segment = request.path_info.strip('/').split('/')[0] if request.path_info.strip('/') else ''
            if first_segment and first_segment != label:
                other_key = f"subdom_tour_exists_{first_segment}"
                other_exists = cache.get(other_key)
                if other_exists is None:
                    other_exists = Tournament.objects.filter(slug=first_segment).exists()
                    cache.set(other_key, other_exists, 300)
                if other_exists:
                    # Path is for a different tournament — don't rewrite
                    return self.get_response(request)

            new_path = f'/{label}{request.path_info}'
            request.path_info = new_path
            request.path = new_path

        return self.get_response(request)
