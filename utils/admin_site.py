"""Custom Django AdminSite, AdminConfig, and auth backend for NekoTab SaaS.

Access tiers
------------
1. **Platform Owner** (``is_superuser=True``) — highest authority.  Sees and
   edits every tournament on the platform.  Only the platform operator should
   hold this flag.

2. **Tournament admin** (owner, org OWNER/ADMIN, tab director, group member)
   — accesses ``/database/`` without needing ``is_staff=True``.  Scoped to
   their own tournaments by every ``ModelAdmin`` that uses
   ``TournamentScopedAdminMixin`` and by the scoped ``UserAdmin``.

3. **Legacy staff** (``is_staff=True``, no superuser) — still admitted for
   backwards-compatibility but treated as a scoped tournament admin.

This module provides:

1. **NekoTabAdminConfig** — sets ``default_site`` so our custom admin site is
   created *before* ``autodiscover()`` runs.

2. **NekoTabAdminSite** — overrides ``has_permission()`` to admit qualifying
   users without ``is_staff``.

3. **TournamentAdminBackend** — grants Django model-level permissions to
   qualifying users so they can browse models in the admin.
"""

import logging

from django.contrib.admin import AdminSite as BaseAdminSite
from django.contrib.admin.apps import AdminConfig

logger = logging.getLogger(__name__)

# App labels whose models tournament admins may browse in the admin.
# Anything outside this set (e.g. ``auth``, ``sessions``) stays visible
# only to superusers / staff.
TOURNAMENT_ADMIN_APP_LABELS = frozenset({
    'tournaments', 'participants', 'venues', 'draw',
    'motions', 'adjfeedback', 'adjallocation', 'availability',
    'breakqual', 'checkins', 'importer', 'options',
    'privateurls', 'results', 'actionlog', 'users',
    'organizations', 'registration', 'notifications',
})


# ── Helper ──────────────────────────────────────────────────────────────

def _user_can_admin_any_tournament(user):
    """Return True if *user* owns or is an org OWNER/ADMIN for any tournament.

    Result is cached on the user object for the current request to avoid
    repeated DB hits when called from multiple permission checks.
    """
    cached = getattr(user, '_nekotab_can_admin_any', None)
    if cached is not None:
        return cached

    from django.db.models import Q
    from organizations.models import OrganizationMembership
    from tournaments.models import Tournament, TournamentStaffMembership
    from users.models import Membership

    org_admin_ids = OrganizationMembership.objects.filter(
        user=user,
        role__in=[OrganizationMembership.Role.OWNER,
                  OrganizationMembership.Role.ADMIN],
    ).values_list('organization_id', flat=True)

    result = Tournament.objects.filter(
        Q(owner=user) | Q(organization_id__in=org_admin_ids),
    ).exists()

    # Also allow users with a tournament staff membership (tab director etc.)
    # or any group membership (old permission system).
    if not result:
        result = TournamentStaffMembership.objects.filter(user=user).exists()
    if not result:
        result = Membership.objects.filter(user=user).exists()

    # Cache on user object (lives only for the current request)
    user._nekotab_can_admin_any = result
    return result


# ── Custom AdminSite ────────────────────────────────────────────────────

class NekoTabAdminSite(BaseAdminSite):
    """AdminSite that admits org OWNER/ADMIN and tournament owners.

    Extends the default ``has_permission()`` check so that qualifying users
    can access ``/database/`` without needing ``is_staff=True``.
    """

    site_header = 'NekoTab Database'
    site_title = 'NekoTab Database'

    def has_permission(self, request):
        user = request.user
        if not hasattr(user, 'is_active') or not user.is_active:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return _user_can_admin_any_tournament(user)


# ── Custom AdminConfig ──────────────────────────────────────────────────

class NekoTabAdminConfig(AdminConfig):
    """AppConfig that sets ``default_site`` to :class:`NekoTabAdminSite`.

    Use ``'utils.admin_site.NekoTabAdminConfig'`` in ``INSTALLED_APPS``
    instead of ``'django.contrib.admin'`` so the custom admin site is
    created *before* ``autodiscover()`` runs and all ``@admin.register()``
    decorators attach their models to it.
    """

    default_site = 'utils.admin_site.NekoTabAdminSite'


# ── Auth Backend ────────────────────────────────────────────────────────

class TournamentAdminBackend:
    """Authentication backend granting admin model permissions to tournament
    admins.

    This backend does NOT handle authentication (``authenticate()`` returns
    ``None``).  It only provides ``has_perm`` / ``has_module_perms`` so that
    qualifying users can browse models inside the Django admin.

    Permissions are limited to the app labels in
    ``TOURNAMENT_ADMIN_APP_LABELS``.
    """

    def authenticate(self, request, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not getattr(user_obj, 'is_active', False):
            return False
        app_label = perm.split('.')[0] if '.' in perm else ''
        if app_label not in TOURNAMENT_ADMIN_APP_LABELS:
            return False
        return _user_can_admin_any_tournament(user_obj)

    def has_module_perms(self, user_obj, app_label):
        if not getattr(user_obj, 'is_active', False):
            return False
        if app_label not in TOURNAMENT_ADMIN_APP_LABELS:
            return False
        return _user_can_admin_any_tournament(user_obj)
