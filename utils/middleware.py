import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponseNotFound, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from tournaments.models import Round, Tournament

logger = logging.getLogger(__name__)

# Compiled once; matches RFC-952/1123-compliant DNS labels.
_DNS_LABEL_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$')


def is_slug_dns_safe(slug):
    """Return True if *slug* can be used as a DNS subdomain label.

    Rules: lowercase alphanumeric + hyphens, no underscores, must start and
    end with an alphanumeric character.  Single-char slugs like ``a`` are fine.
    """
    if not slug:
        return False
    return '_' not in slug and bool(_DNS_LABEL_RE.match(slug.lower()))


def _is_base_domain(host, base_domain):
    """Return True if *host* is the bare base domain (no subdomain)."""
    return host == base_domain or host == f'www.{base_domain}'


class DebateMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if 'tournament_slug' not in view_kwargs:
            return None
        if request.path.split('/')[1] == 'api':
            return None

        slug = view_kwargs['tournament_slug']

        # ------------------------------------------------------------------
        # Rule: Redirect path-based access → subdomain  (exactly ONE hop)
        #
        # Conditions that MUST ALL be true:
        #   1. Subdomain routing is globally enabled
        #   2. The slug is DNS-safe
        #   3. The request is on the bare base domain (not already a subdomain)
        #   4. The client issued a safe method (GET / HEAD)
        #   5. SubdomainTournamentMiddleware did NOT already tag this request
        #      (i.e. we are not inside a rewritten subdomain request)
        # ------------------------------------------------------------------
        subdomain_on = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
        base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
        already_subdomain = getattr(request, 'subdomain_tournament', None)

        if (subdomain_on and base_domain
                and not already_subdomain
                and request.method in ('GET', 'HEAD')
                and is_slug_dns_safe(slug)):
            # Extra guard: only redirect if we are truly on the base domain.
            # Behind a proxy the Host header is preserved (Heroku, Cloudflare).
            try:
                host = request.get_host().split(':')[0].lower()
            except Exception:
                host = ''

            if _is_base_domain(host, base_domain):
                full_path = request.get_full_path()
                slug_prefix = f'/{slug}/'
                if full_path.startswith(slug_prefix):
                    clean_path = '/' + full_path[len(slug_prefix):]
                elif full_path == f'/{slug}':
                    clean_path = '/'
                else:
                    clean_path = full_path
                target = f'https://{slug.lower()}.{base_domain}{clean_path}'
                logger.debug("DebateMiddleware: redirecting %s → %s", request.path, target)
                return HttpResponsePermanentRedirect(target)

        # ------------------------------------------------------------------
        # Resolve and cache the tournament object
        # ------------------------------------------------------------------
        cached_key = "%s_%s" % (slug, 'object')
        cached_tournament = cache.get(cached_key)

        if cached_tournament:
            request.tournament = cached_tournament
        else:
            tournament = self._resolve_tournament(slug, request)
            if tournament is None:
                return self._tournament_not_found_response(slug, request)
            request.tournament = tournament
            cache.set(cached_key, tournament, 3600)

        # ------------------------------------------------------------------
        # Visibility gate – return 404 (not 403) to avoid leaking existence
        # ------------------------------------------------------------------
        user = getattr(request, 'user', None)
        if not self._user_can_see(request.tournament, user):
            return self._tournament_not_found_response(slug, request)

        # ------------------------------------------------------------------
        # Resolve round (if present)
        # ------------------------------------------------------------------
        if 'round_seq' in view_kwargs:
            round_key = "%s_%s_%s" % (slug, view_kwargs['round_seq'], 'object')
            cached_round = cache.get(round_key)
            if cached_round:
                request.round = cached_round
            else:
                request.round = get_object_or_404(
                    Round, tournament=request.tournament,
                    seq=view_kwargs['round_seq'])
                cache.set(round_key, request.round, 3600)

        return None

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _user_can_see(tournament, user):
        """Return True if *user* is allowed to see *tournament*.

        Uses the same visibility queryset as ``TournamentQuerySet.visible_to``
        but avoids an extra DB hit when the tournament is already resolved.
        """
        if tournament.is_listed:
            return True
        if user is None or not getattr(user, 'is_authenticated', False):
            return False
        if user.is_superuser:
            return True
        # Owner check via the tournament field
        if hasattr(tournament, 'owner_id') and tournament.owner_id == user.pk:
            return True
        # Permission or membership check
        from users.models import Membership, UserPermission  # noqa: E402
        if UserPermission.objects.filter(user=user, tournament=tournament).exists():
            return True
        if Membership.objects.filter(user=user, group__tournament=tournament).exists():
            return True
        return False

    @staticmethod
    def _resolve_tournament(slug, request):
        """Try exact match, then case-insensitive fallback.  Returns
        Tournament or None."""
        try:
            return Tournament.objects.get(slug=slug)
        except Tournament.DoesNotExist:
            pass

        # Case-insensitive fallback (covers subdomain-lowered hostnames)
        try:
            tournament = Tournament.objects.get(slug__iexact=slug)
            logger.info("DebateMiddleware: case-insensitive fallback "
                        "'%s' → '%s'", slug, tournament.slug)
            return tournament
        except (Tournament.DoesNotExist, Tournament.MultipleObjectsReturned):
            pass

        logger.warning(
            "Tournament not found: slug=%s, path=%s, user=%s, ip=%s, referer=%s",
            slug, request.path,
            getattr(request.user, 'username', 'anonymous'),
            request.META.get('REMOTE_ADDR', 'unknown'),
            request.META.get('HTTP_REFERER', 'none'),
        )
        return None

    @staticmethod
    def _tournament_not_found_response(slug, request):
        try:
            html = render_to_string('errors/tournament_not_found.html', {
                'slug': slug, 'request': request,
            })
            return HttpResponseNotFound(html)
        except Exception:
            raise Http404(f"Tournament '{slug}' does not exist.")


def get_subdomain_url(tournament_slug, path='/', scheme='https'):
    """Build a full subdomain URL for a tournament.

    Returns the URL string, or ``None`` when subdomain routing is disabled
    **or the slug is not DNS-safe**.
    """
    if not getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False):
        return None
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
    if not base_domain:
        return None
    if not is_slug_dns_safe(tournament_slug):
        return None
    if not path.startswith('/'):
        path = '/' + path
    # Always lowercase the slug in the hostname (DNS is case-insensitive).
    return f"{scheme}://{tournament_slug.lower()}.{base_domain}{path}"


class SubdomainTournamentMiddleware:
    """Allows accessing tournaments via subdomains, e.g.
    ``https://my-tournament.nekotab.app/motions/`` is internally rewritten so
    Django sees ``/my-tournament/motions/``.

    Key invariants enforced here:

    * **No redirect loops.**  Subdomain hosts are inherently lowercase (DNS is
      case-insensitive).  Exact slug mismatches due to case are resolved by a
      case-insensitive DB lookup rather than a redirect.
    * Requests on a recognised tournament subdomain get
      ``request.subdomain_tournament`` set to the slug *as stored in the DB*
      so downstream code (templates, ``DebateMiddleware``) can detect it.
    * Global routes (``/static/``, ``/admin/``, etc.) are never rewritten.
    """

    RESERVED_SUBDOMAINS_DEFAULT = {
        'www', 'admin', 'api', 'static', 'media', 'jet', 'database',
    }

    BAD_PREFIXES = (
        '/static/', '/media/', '/database/', '/api/',
        '/analytics/', '/accounts/', '/campaigns/', '/notifications/',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
        self.base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
        reserved = getattr(settings, 'RESERVED_SUBDOMAINS', None)
        self.reserved = set(reserved) if reserved is not None else self.RESERVED_SUBDOMAINS_DEFAULT
        self.slug_re = _DNS_LABEL_RE

    def _extract_tournament_subdomain(self, request):
        """Extract tournament slug from the Host header subdomain.
        Returns the slug string (always lowercase), or None."""
        try:
            host = request.get_host().split(':')[0].lower()
        except Exception:
            return None

        if not host or not host.endswith(self.base_domain):
            return None

        subpart = host[:-len(self.base_domain)].rstrip('.')
        if not subpart or '.' in subpart:
            return None

        if subpart in self.reserved or not self.slug_re.match(subpart):
            return None

        return subpart

    def __call__(self, request):
        # Always initialise so downstream code can rely on the attribute.
        request.subdomain_tournament = None

        if not self.enabled or not self.base_domain:
            return self.get_response(request)

        label = self._extract_tournament_subdomain(request)
        if not label:
            return self.get_response(request)

        # -----------------------------------------------------------------
        # Verify the slug belongs to a real tournament.
        #
        # Because DNS hostnames are case-insensitive, the *label* extracted
        # from the Host header is always lowercase.  The DB slug may have
        # mixed case.  We therefore use a **case-insensitive** existence
        # check and NEVER redirect to a differently-cased hostname (that
        # would loop because browsers re-lowercase the host).
        # -----------------------------------------------------------------
        cache_key = f"subdom_tour_exists_{label}"
        cached = cache.get(cache_key)
        if cached is None:
            # Try exact first (fast path), then case-insensitive.
            cached = (
                Tournament.objects.filter(slug=label).exists()
                or Tournament.objects.filter(slug__iexact=label).exists()
            )
            cache.set(cache_key, cached, 300)

        if not cached:
            logger.warning(
                "Subdomain tournament not found: subdomain=%s, path=%s, "
                "ip=%s, referer=%s",
                label, request.path,
                request.META.get('REMOTE_ADDR', 'unknown'),
                request.META.get('HTTP_REFERER', 'none'),
            )
            try:
                html = render_to_string('errors/subdomain_404.html', {
                    'subdomain': label,
                    'base_domain': self.base_domain,
                })
                return HttpResponseNotFound(html)
            except Exception:
                return HttpResponseNotFound(
                    f'<h1>Tournament not found</h1>'
                    f'<p>No tournament exists at '
                    f'<strong>{label}.{self.base_domain}</strong>.</p>'
                    f'<p><a href="https://{self.base_domain}/">Go to NekoTab '
                    f'home</a></p>'
                )

        # Tag the request.  Use the lowercase label (matches the hostname the
        # user actually sees in their browser bar).
        request.subdomain_tournament = label

        # -----------------------------------------------------------------
        # Prefix the path so Django's URL resolver matches the existing
        # <slug:tournament_slug>/... patterns — unless already prefixed or
        # the path is a global route.
        # -----------------------------------------------------------------
        if request.path_info.startswith(self.BAD_PREFIXES):
            return self.get_response(request)

        if not request.path_info.startswith(f'/{label}/'):
            # Guard: if the first segment is *another* tournament's slug,
            # don't blindly prepend ours (prevents cross-tournament
            # confusion on subdomain).
            first_seg = request.path_info.strip('/').split('/')[0] if request.path_info.strip('/') else ''
            if first_seg and first_seg != label:
                seg_key = f"subdom_tour_exists_{first_seg}"
                seg_exists = cache.get(seg_key)
                if seg_exists is None:
                    seg_exists = Tournament.objects.filter(slug=first_seg).exists()
                    cache.set(seg_key, seg_exists, 300)
                if seg_exists:
                    return self.get_response(request)

            new_path = f'/{label}{request.path_info}'
            request.path_info = new_path
            request.path = new_path

        return self.get_response(request)
