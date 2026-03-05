"""Multi-tenant isolation helpers for the Django admin.

Exports
-------
get_admin_tournaments_for_user(user) → QuerySet[Tournament]
    Single source of truth for which tournaments a user may administer.

TournamentScopedAdminMixin
    Drop-in mixin for any ``ModelAdmin`` whose model has a (possibly
    indirect) FK chain to ``Tournament``.

getattr_path(obj, dotted_path)
    Safely resolves nested attribute paths like ``"round.tournament.id"``.
"""

from django.contrib.admin import SimpleListFilter
from django.db.models import Q


# ── Single source of truth ──────────────────────────────────────────────

def get_admin_tournaments_for_user(user):
    """Return a ``QuerySet[Tournament]`` the *user* may administer.

    Rules (evaluated with a single SQL query):

    * **Superusers** → all tournaments.
    * **Tournament owner** → tournaments where ``owner == user``.
    * **Org OWNER / ADMIN** → tournaments whose organisation the user
      belongs to with role OWNER or ADMIN.
    * **Explicit permission** → tournaments where the user has at least one
      ``UserPermission`` row (indicates they were explicitly granted
      access).
    """
    from tournaments.models import Tournament

    if user.is_superuser:
        return Tournament.objects.all()

    from organizations.models import OrganizationMembership
    from users.models import UserPermission

    org_admin_org_ids = OrganizationMembership.objects.filter(
        user=user,
        role__in=[
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
        ],
    ).values_list('organization_id', flat=True)

    perm_tournament_ids = (
        UserPermission.objects.filter(user=user)
        .values_list('tournament_id', flat=True)
        .distinct()
    )

    return Tournament.objects.filter(
        Q(owner=user)
        | Q(organization_id__in=org_admin_org_ids)
        | Q(id__in=perm_tournament_ids)
    ).distinct()


# ── Attribute-path resolver ─────────────────────────────────────────────

def getattr_path(obj, dotted_path):
    """Resolve a dotted attribute path on *obj*.

    >>> getattr_path(speaker_score, "debate_team.debate.round.tournament.id")
    42
    """
    current = obj
    for attr in dotted_path.split('.'):
        if current is None:
            return None
        current = getattr(current, attr, None)
    return current


# ── Reusable mixin ──────────────────────────────────────────────────────

class TournamentScopedAdminMixin:
    """Mixin for ``ModelAdmin`` classes whose model is tournament-scoped.

    Set ``tournament_lookup`` to the ORM lookup path from the model to its
    ``Tournament`` FK.  Examples::

        tournament_lookup = "tournament"               # direct FK
        tournament_lookup = "round__tournament"         # one hop
        tournament_lookup = "debate__round__tournament"  # two hops

    The mixin:

    * Filters ``get_queryset()`` so non-superusers only see their objects.
    * Overrides ``has_{view,change,delete}_permission`` for per-object
      checks (blocks direct-URL access to foreign objects).
    * Filters FK drop-downs via ``formfield_for_foreignkey()`` so that
      foreign-key widgets only list objects from allowed tournaments.
    """

    tournament_lookup = "tournament"

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_allowed_tournament_ids(self, request):
        """Return a list of allowed tournament PKs (cached on *request*)."""
        cache_attr = '_admin_allowed_tournament_ids'
        ids = getattr(request, cache_attr, None)
        if ids is not None:
            return ids
        ids = list(
            get_admin_tournaments_for_user(request.user)
            .values_list('id', flat=True)
        )
        setattr(request, cache_attr, ids)
        return ids

    def _obj_tournament_id(self, obj):
        """Resolve the tournament PK from *obj* via ``tournament_lookup``."""
        dotted = self.tournament_lookup.replace('__', '.') + '.id'
        return getattr_path(obj, dotted)

    def _obj_in_allowed(self, request, obj):
        tid = self._obj_tournament_id(obj)
        return tid is not None and tid in self._get_allowed_tournament_ids(request)

    # ── QuerySet filtering ──────────────────────────────────────────────

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        lookup = f"{self.tournament_lookup}__id__in"
        return qs.filter(**{lookup: self._get_allowed_tournament_ids(request)})

    # ── Per-object permissions ──────────────────────────────────────────

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_view_permission(request, obj)
        return self._obj_in_allowed(request, obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_change_permission(request, obj)
        return self._obj_in_allowed(request, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return super().has_delete_permission(request, obj)
        return self._obj_in_allowed(request, obj)

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return super().has_add_permission(request)

    # ── FK drop-down filtering ──────────────────────────────────────────

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter FK widgets to only show objects from allowed tournaments."""
        if not request.user.is_superuser:
            from tournaments.models import Round, Tournament

            allowed_ids = self._get_allowed_tournament_ids(request)
            related_model = db_field.related_model

            if related_model is Tournament:
                kwargs['queryset'] = Tournament.objects.filter(id__in=allowed_ids)
            elif related_model is Round:
                kwargs['queryset'] = Round.objects.filter(
                    tournament_id__in=allowed_ids,
                ).select_related('tournament')
            else:
                # Auto-detect common FK patterns on the related model
                field_names = {f.name for f in related_model._meta.get_fields()}
                if 'tournament' in field_names:
                    qs = kwargs.get('queryset') or related_model._default_manager.all()
                    kwargs['queryset'] = qs.filter(tournament_id__in=allowed_ids)
                elif 'round' in field_names:
                    try:
                        fld = related_model._meta.get_field('round')
                        if hasattr(fld, 'related_model') and fld.related_model.__name__ == 'Round':
                            qs = kwargs.get('queryset') or related_model._default_manager.all()
                            kwargs['queryset'] = qs.filter(round__tournament_id__in=allowed_ids)
                    except Exception:
                        pass

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ── List-filter scoping ─────────────────────────────────────────────

    def get_list_filter(self, request):
        """Replace FK-based list filters with tenant-scoped versions.

        Django's default ``RelatedFieldListFilter`` for FK columns shows
        **all** related objects regardless of the queryset.  We replace
        tournament/round string filters with custom ``SimpleListFilter``
        subclasses that only list allowed objects.
        """
        if request.user.is_superuser:
            return super().get_list_filter(request)

        from tournaments.models import Round, Tournament

        filters = list(super().get_list_filter(request))
        allowed_ids = self._get_allowed_tournament_ids(request)
        new_filters = []
        for f in filters:
            if f == 'tournament':
                new_filters.append(
                    _make_scoped_tournament_filter(allowed_ids))
            elif f == 'round':
                new_filters.append(
                    _make_scoped_round_filter(allowed_ids))
            else:
                new_filters.append(f)
        return new_filters


def _make_scoped_tournament_filter(allowed_ids):
    """Return a SimpleListFilter that only shows allowed tournaments."""
    class ScopedTournamentFilter(SimpleListFilter):
        title = 'tournament'
        parameter_name = 'tournament__id__exact'

        def lookups(self, request, model_admin):
            from tournaments.models import Tournament
            return [
                (str(t.pk), str(t))
                for t in Tournament.objects.filter(id__in=allowed_ids)
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(tournament__id=self.value())
            return queryset

    return ScopedTournamentFilter


def _make_scoped_round_filter(allowed_ids):
    """Return a SimpleListFilter that only shows rounds from allowed tournaments."""
    class ScopedRoundFilter(SimpleListFilter):
        title = 'round'
        parameter_name = 'round__id__exact'

        def lookups(self, request, model_admin):
            from tournaments.models import Round
            return [
                (str(r.pk), str(r))
                for r in Round.objects.filter(
                    tournament_id__in=allowed_ids,
                ).select_related('tournament')
            ]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(round__id=self.value())
            return queryset

    return ScopedRoundFilter


# ── Organization-scoped mixin ───────────────────────────────────────────

class OrganizationScopedAdminMixin:
    """Mixin for admin classes that should be scoped to the user's orgs.

    Applicable to ``Organization`` and ``OrganizationMembership`` admins.
    Non-superusers only see organisations where they are OWNER or ADMIN.
    """

    def _get_allowed_org_ids(self, request):
        cache_attr = '_admin_allowed_org_ids'
        ids = getattr(request, cache_attr, None)
        if ids is not None:
            return ids
        from organizations.models import OrganizationMembership
        ids = list(
            OrganizationMembership.objects.filter(
                user=request.user,
                role__in=[
                    OrganizationMembership.Role.OWNER,
                    OrganizationMembership.Role.ADMIN,
                ],
            ).values_list('organization_id', flat=True)
        )
        setattr(request, cache_attr, ids)
        return ids
