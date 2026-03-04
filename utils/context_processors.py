from django.conf import settings

from tournaments.models import Tournament


def _annotate_tournament_access(tournaments, user):
    """Annotate each tournament with per-user access flags for template use.

    Adds to each tournament object:
      - ``user_can_admin``: True if user has admin-level access
      - ``user_can_assist``: True if user has assistant-level access
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        for t in tournaments:
            t.user_can_admin = False
            t.user_can_assist = False
        return tournaments

    if user.is_superuser:
        for t in tournaments:
            t.user_can_admin = True
            t.user_can_assist = True
        return tournaments

    from organizations.models import OrganizationMembership
    from users.models import Membership, UserPermission

    # Batch-fetch org memberships for all orgs the user belongs to
    user_org_roles = dict(
        OrganizationMembership.objects.filter(user=user)
        .values_list('organization_id', 'role')
    )
    # Batch-fetch tournament IDs where user has direct permissions/memberships
    perm_tournament_ids = set(
        UserPermission.objects.filter(user=user)
        .values_list('tournament_id', flat=True)
    )
    group_tournament_ids = set(
        Membership.objects.filter(user=user)
        .values_list('group__tournament_id', flat=True)
    )

    ADMIN_ROLES = {OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN}
    ASSIST_ROLES = ADMIN_ROLES | {OrganizationMembership.Role.MEMBER}

    for t in tournaments:
        org_role = user_org_roles.get(t.organization_id)
        is_owner = hasattr(t, 'owner_id') and t.owner_id == user.pk
        has_direct = (t.pk in perm_tournament_ids or t.pk in group_tournament_ids)

        t.user_can_admin = is_owner or (org_role in ADMIN_ROLES) or has_direct
        t.user_can_assist = is_owner or (org_role in ASSIST_ROLES) or has_direct

    return tournaments


def debate_context(request):

    subdomain_enabled = getattr(settings, 'SUBDOMAIN_TOURNAMENTS_ENABLED', False)
    base_domain = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', '')

    user = getattr(request, 'user', None)

    context = {
        'tabbycat_version': settings.TABBYCAT_VERSION or "",
        'tabbycat_codename': settings.TABBYCAT_CODENAME or "no codename",
        'all_tournaments': _annotate_tournament_access(
            list(Tournament.objects.visible_to(user)), user,
        ),
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
