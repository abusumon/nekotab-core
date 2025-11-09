from django.conf import settings

from tournaments.models import Tournament


def debate_context(request):

    context = {
        'tabbycat_version': settings.TABBYCAT_VERSION or "",
        'tabbycat_codename': settings.TABBYCAT_CODENAME or "no codename",
        'all_tournaments': Tournament.objects.filter(active=True),
        'disable_sentry': getattr(settings, 'DISABLE_SENTRY', False),
        'on_local': getattr(settings, 'ON_LOCAL', False),
        'hmr': getattr(settings, 'USE_WEBPACK_SERVER', False),
        # SEO defaults
        'seo_site_name': 'NekoTab Debate Tabulation',
        'seo_keywords': 'debate tab, debate tabulation, parliamentary debating, BP motions, adjudicator allocation, debate tournament software, asian parliamentary, australs debating, british parliamentary, debate results live',
        'seo_base_url': getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app'),
    }

    # Canonical URL: normalize to SITE_BASE_URL + request.path
    try:
        path = request.path if hasattr(request, 'path') else '/'
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
