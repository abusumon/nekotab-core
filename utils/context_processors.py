from django.conf import settings

from tournaments.models import Tournament


def debate_context(request):

    subdomain_enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')

    user = getattr(request, 'user', None)

    context = {
        'tabbycat_version': settings.TABBYCAT_VERSION or "",
        'tabbycat_codename': settings.TABBYCAT_CODENAME or "no codename",
        'all_tournaments': Tournament.objects.visible_to(user),
        'disable_sentry': getattr(settings, 'DISABLE_SENTRY', False),
        'on_local': getattr(settings, 'ON_LOCAL', False),
        'hmr': getattr(settings, 'USE_WEBPACK_SERVER', False),
        'subdomain_enabled': subdomain_enabled,
        'subdomain_base_domain': base_domain,
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

    return context
