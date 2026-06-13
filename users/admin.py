from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group as AuthGroup
from django.db.models import Q
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from .models import Group, Membership, UserPermission

from utils.admin_tenant import TournamentScopedAdminMixin


def _is_platform_owner(user):
    """True if *user* holds the highest platform authority (is_superuser).

    Centralised so every admin check uses the same gate.  Only one person
    should have this — the platform operator.  Everyone else (tournament
    creators, tab directors) gets automatically scoped access via the
    tournament ownership / invitation system.
    """
    return getattr(user, 'is_superuser', False)


# ==============================================================================
# Authentication and Authorization
# ==============================================================================

admin.site.unregister(AuthGroup)  # Not used — NekoTab has its own Group model


class UserPermissionInline(admin.TabularInline):
    model = UserPermission
    fields = ('permission', 'tournament')
    extra = 0


class MembershipInline(admin.TabularInline):
    model = Membership
    fields = ('group',)
    extra = 0


class UserChangeFormExtended(UserChangeForm):
    group_set = ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'is_superuser' in self.fields:
            self.fields['is_superuser'].label = _("Platform Owner")
            self.fields['is_superuser'].help_text = _(
                "Designates that this user has the highest authority on the "
                "entire platform — they can see and edit every tournament's "
                "data. Only the platform operator should have this flag."
            )
        if 'is_staff' in self.fields:
            self.fields['is_staff'].label = _("Legacy database access")
            self.fields['is_staff'].help_text = _(
                "Grants access to the database editor via the old is_staff "
                "path. Deprecated — tournament owners and tab directors "
                "receive database access automatically through the invitation "
                "system without needing this flag."
            )


class UserCreationFormExtended(UserCreationForm):
    group_set = ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'is_superuser' in self.fields:
            self.fields['is_superuser'].label = _("Platform Owner")
        if 'is_staff' in self.fields:
            self.fields['is_staff'].label = _("Legacy database access")


# Fieldsets shown to the platform owner (full access)
_FIELDSETS_OWNER = (
    (_('Personal info'), {'fields': ('username', 'email', 'password')}),
    (_('Platform access'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
)

# Fieldsets shown to tournament admins / tab directors (no platform flags)
_FIELDSETS_SCOPED = (
    (_('Personal info'), {'fields': ('username', 'email', 'password')}),
    (_('Status'), {'fields': ('is_active',)}),
    (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
)

_ADD_FIELDSETS_OWNER = (
    (None, {
        'fields': (
            'username', 'password1', 'password2', 'email',
            'is_staff', 'is_superuser', 'group_set',
        ),
    }),
)

_ADD_FIELDSETS_SCOPED = (
    (None, {
        'fields': ('username', 'password1', 'password2', 'email', 'group_set'),
    }),
)


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_superuser')
    inlines = (UserPermissionInline, MembershipInline)

    add_form_template = 'admin/change_form.html'
    add_form = UserCreationFormExtended
    form = UserChangeFormExtended

    # Defaults; get_fieldsets / get_add_fieldsets select the right set per request
    fieldsets = _FIELDSETS_SCOPED
    add_fieldsets = _ADD_FIELDSETS_SCOPED

    # ── Fieldset selection ──────────────────────────────────────────────

    def get_fieldsets(self, request, obj=None):
        return _FIELDSETS_OWNER if _is_platform_owner(request.user) else _FIELDSETS_SCOPED

    def get_add_fieldsets(self, request):
        return _ADD_FIELDSETS_OWNER if _is_platform_owner(request.user) else _ADD_FIELDSETS_SCOPED

    # ── QuerySet scoping ────────────────────────────────────────────────

    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related('group_set')
        if _is_platform_owner(request.user):
            return qs

        # Non-platform-owners see only users who share their tournaments,
        # plus themselves.  This prevents cross-tournament data leakage.
        from tournaments.models import TournamentStaffMembership
        from utils.admin_tenant import get_admin_tournaments_for_user

        allowed_ids = list(
            get_admin_tournaments_for_user(request.user).values_list('id', flat=True)
        )
        perm_user_ids = (
            UserPermission.objects.filter(tournament_id__in=allowed_ids)
            .values_list('user_id', flat=True)
        )
        membership_user_ids = (
            Membership.objects.filter(group__tournament_id__in=allowed_ids)
            .values_list('user_id', flat=True)
        )
        staff_user_ids = (
            TournamentStaffMembership.objects.filter(tournament_id__in=allowed_ids)
            .values_list('user_id', flat=True)
        )
        return qs.filter(
            Q(id=request.user.pk)
            | Q(id__in=perm_user_ids)
            | Q(id__in=membership_user_ids)
            | Q(id__in=staff_user_ids)
        ).distinct()

    # ── Permission gates ────────────────────────────────────────────────

    def has_add_permission(self, request):
        # Direct user creation is reserved for the platform owner.
        # Everyone else invites tournament staff via the invitation URL.
        return _is_platform_owner(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_platform_owner(request.user)

    def has_change_permission(self, request, obj=None):
        if _is_platform_owner(request.user):
            return True
        if obj is None:
            return True  # allow the list view
        # Scoped users may only edit users visible in their queryset
        # (enforced by get_queryset; this is a belt-and-braces object check)
        return obj.pk == request.user.pk or not obj.is_superuser

    def has_view_permission(self, request, obj=None):
        if _is_platform_owner(request.user):
            return True
        if obj is None:
            return True
        return not obj.is_superuser


# ==============================================================================
# UserPermission and Group
# ==============================================================================

@admin.register(UserPermission)
class UserPermissionAdmin(TournamentScopedAdminMixin, admin.ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('user', 'permission', 'tournament')


@admin.register(Group)
class GroupAdmin(TournamentScopedAdminMixin, admin.ModelAdmin):
    tournament_lookup = 'tournament'
    list_display = ('name', 'tournament')


User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
