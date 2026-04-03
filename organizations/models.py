import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.models import UniqueConstraint

logger = logging.getLogger(__name__)


class Organization(models.Model):
    """A tenant that groups one or more tournaments under a single billing /
    access-control umbrella.

    Every tournament MUST belong to exactly one organization (enforced at the
    application layer; the FK is nullable only to allow a graceful migration
    period for legacy data).

    An organization can have multiple members with different roles.  The owner
    of the organization has full control over all tournaments within it.
    """

    name = models.CharField(
        max_length=200,
        verbose_name=_("name"),
        help_text=_("Display name of the organization, e.g. \"Oxford Union Debate Society\""),
    )
    slug = models.SlugField(
        unique=True,
        max_length=80,
        verbose_name=_("slug"),
        help_text=_("URL-safe identifier for the organization."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    # ── Workspace support ───────────────────────────────────────────────
    is_workspace_enabled = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("workspace enabled"),
        help_text=_("When enabled, this organization is accessible via its own subdomain."),
    )
    description = models.TextField(
        blank=True, default="",
        verbose_name=_("description"),
    )
    logo = models.ImageField(
        upload_to='org_logos/', blank=True, null=True,
        verbose_name=_("logo"),
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("active"),
        help_text=_("Inactive organizations are hidden from the registration flow."),
    )
    deactivation_reason = models.TextField(
        blank=True, default='',
        verbose_name=_("deactivation reason"),
    )

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.is_workspace_enabled:
            from tournaments.models import Tournament
            if Tournament.objects.filter(slug__iexact=self.slug).exists():
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'slug': _("This slug is already in use by a tournament."),
                })


class OrganizationMembership(models.Model):
    """Maps a user to an organization with a specific role.

    Roles cascade **downward**: an org OWNER implicitly has ADMIN powers, an
    ADMIN implicitly has MEMBER powers, etc.

    Role semantics:
    - OWNER  → full control: billing, delete org, manage members + all tournaments
    - ADMIN  → manage tournaments + members (except changing owner)
    - MEMBER → access all tournaments in the org (view + edit per tournament perms)
    - VIEWER → read-only access to all tournaments in the org
    """

    class Role(models.TextChoices):
        OWNER     = 'owner',     _("Owner")
        ADMIN     = 'admin',     _("Admin")
        TABMASTER = 'tabmaster', _("Tabmaster")
        EDITOR    = 'editor',    _("Editor")
        VIEWER    = 'viewer',    _("Viewer")
        # Legacy alias — existing DB rows use 'member'; treated as EDITOR level.
        MEMBER    = 'member',    _("Member")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_("organization"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='org_memberships',
        verbose_name=_("user"),
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name=_("role"),
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name=_("joined at"))

    class Meta:
        verbose_name = _("organization membership")
        verbose_name_plural = _("organization memberships")
        constraints = [
            UniqueConstraint(fields=['organization', 'user']),
        ]

    def __str__(self):
        return f"{self.user} → {self.organization} ({self.get_role_display()})"

    # -- Role hierarchy helpers -----------------------------------------------

    ROLE_HIERARCHY = {
        Role.OWNER:     5,
        Role.ADMIN:     4,
        Role.TABMASTER: 3,
        Role.EDITOR:    2,
        Role.MEMBER:    2,   # legacy alias — same level as EDITOR
        Role.VIEWER:    1,
    }

    @property
    def role_level(self):
        return self.ROLE_HIERARCHY.get(self.role, 0)

    def has_role_at_least(self, minimum_role):
        """Return True if this membership's role is >= *minimum_role*."""
        min_level = self.ROLE_HIERARCHY.get(minimum_role, 0)
        return self.role_level >= min_level

    @property
    def is_admin_or_above(self):
        """Template-friendly shortcut: True if ADMIN or OWNER."""
        return self.has_role_at_least(self.Role.ADMIN)


# ---------------------------------------------------------------------------
# Helper functions (importable from anywhere)
# ---------------------------------------------------------------------------

def get_user_org_role(user, organization):
    """Return the OrganizationMembership.Role for *user* in *organization*,
    or None if the user is not a member."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    try:
        membership = OrganizationMembership.objects.get(
            organization=organization, user=user,
        )
        return membership.role
    except OrganizationMembership.DoesNotExist:
        return None


def user_is_org_member(user, organization):
    """Return True if *user* has any role in *organization*."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    return OrganizationMembership.objects.filter(
        organization=organization, user=user,
    ).exists()


def user_is_org_admin(user, organization):
    """Return True if *user* is ADMIN or OWNER of *organization*."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        role__in=[OrganizationMembership.Role.OWNER, OrganizationMembership.Role.ADMIN],
    ).exists()


def user_is_org_owner(user, organization):
    """Return True if *user* is the OWNER of *organization*."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        role=OrganizationMembership.Role.OWNER,
    ).exists()


def get_user_organizations(user):
    """Return a queryset of organizations the *user* belongs to."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return Organization.objects.none()
    return Organization.objects.filter(
        memberships__user=user,
    ).distinct()
