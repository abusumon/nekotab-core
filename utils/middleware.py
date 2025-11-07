import re

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from tournaments.models import Round, Tournament


class DebateMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if 'tournament_slug' in view_kwargs and request.path.split('/')[1] != 'api':
            cached_key = "%s_%s" % (view_kwargs['tournament_slug'], 'object')
            cached_tournament_object = cache.get(cached_key)

            if cached_tournament_object:
                request.tournament = cached_tournament_object
            else:
                request.tournament = get_object_or_404(
                    Tournament,
                    slug=view_kwargs['tournament_slug'])
                cache.set(cached_key, request.tournament, None)

            if 'round_seq' in view_kwargs:
                cached_key = "%s_%s_%s" % (view_kwargs['tournament_slug'],
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


class SubdomainTournamentMiddleware(object):
    """
    Allows accessing tournaments using subdomains, e.g.
    https://ndf-nationals-2025.example.com/teams/ will be internally
    rewritten to https://example.com/ndf-nationals-2025/teams/

    This is a transparent path prefixer and does not change URL reversing.
    Enable by setting SUBDOMAIN_TOURNAMENTS_ENABLED=true and
    SUBDOMAIN_BASE_DOMAIN=nekotab.app (or your root domain).
    """

    RESERVED_SUBDOMAINS_DEFAULT = {
        'www', 'admin', 'api', 'static', 'media', 'jet', 'database'
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
        self.base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')
        reserved = getattr(settings, 'RESERVED_SUBDOMAINS', None)
        if reserved is None:
            self.reserved = self.RESERVED_SUBDOMAINS_DEFAULT
        else:
            self.reserved = set(reserved)
        self.slug_re = re.compile(r'^[a-z0-9-]+$')

    def __call__(self, request):
        # Short-circuit if feature disabled or misconfigured
        if not self.enabled or not self.base_domain:
            return self.get_response(request)

        try:
            host = request.get_host().split(':')[0]
        except Exception:
            host = ''

        # Only act for subdomains of the configured base domain
        if host and host.endswith(self.base_domain):
            # strip base domain and any trailing dot
            subpart = host[: -len(self.base_domain)]
            if subpart.endswith('.'):
                subpart = subpart[:-1]

            if subpart:
                # Only support single-label subdomains for tournaments
                label = subpart.split('.')[-1]
                if label and label not in self.reserved and self.slug_re.match(label):
                    # Confirm this looks like a real tournament (cached)
                    cache_key = f"subdom_tour_exists_{label}"
                    exists = cache.get(cache_key)
                    if exists is None:
                        exists = Tournament.objects.filter(slug=label).exists()
                        cache.set(cache_key, exists, 60)

                    # Prefix the path if valid and not already prefixed
                    if exists and not request.path_info.startswith(f'/{label}/'):
                        # Avoid interfering with static/media/admin/api
                        bad_prefixes = ('/static/', '/media/', '/admin/', '/database/', '/api')
                        if not request.path_info.startswith(bad_prefixes):
                            new_path = f'/{label}{request.path_info}'
                            request.path_info = new_path
                            request.path = new_path

        return self.get_response(request)
