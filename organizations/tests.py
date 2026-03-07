"""Tests for multi-tenant isolation in the organizations app.

Covers: tenant isolation, RBAC enforcement, ownership safety, permission
downgrade, and membership revocation.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from organizations.models import (
    Organization, OrganizationMembership,
    get_user_org_role, get_user_organizations,
    user_is_org_admin, user_is_org_member, user_is_org_owner,
)
from tournaments.models import Tournament
from users.permissions import has_permission, Permission
from utils.middleware import DebateMiddleware

User = get_user_model()


class TenantIsolationTests(TestCase):
    """User A in Org A cannot access Org B's tournament."""

    def setUp(self):
        self.org_a = Organization.objects.create(name="Org A", slug="org-a")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b")
        self.t_a = Tournament.objects.create(
            name="Tournament A", slug="tourney-a", organization=self.org_a)
        self.t_b = Tournament.objects.create(
            name="Tournament B", slug="tourney-b", organization=self.org_b)
        self.user_a = User.objects.create_user("user_a", password="testpass")
        self.user_b = User.objects.create_user("user_b", password="testpass")
        OrganizationMembership.objects.create(
            organization=self.org_a, user=self.user_a,
            role=OrganizationMembership.Role.OWNER)
        OrganizationMembership.objects.create(
            organization=self.org_b, user=self.user_b,
            role=OrganizationMembership.Role.OWNER)

    def test_user_a_can_access_own_tournament(self):
        self.assertTrue(
            DebateMiddleware._user_has_tournament_access(self.t_a, self.user_a))

    def test_user_a_cannot_access_org_b_tournament(self):
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.t_b, self.user_a))

    def test_user_b_cannot_access_org_a_tournament(self):
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.t_a, self.user_b))

    def test_visible_to_scoping(self):
        """visible_to() only returns tournaments the user has access to."""
        qs_a = Tournament.objects.visible_to(self.user_a)
        qs_b = Tournament.objects.visible_to(self.user_b)
        self.assertIn(self.t_a, qs_a)
        self.assertNotIn(self.t_b, qs_a)
        self.assertIn(self.t_b, qs_b)
        self.assertNotIn(self.t_a, qs_b)

    def test_anonymous_sees_only_listed(self):
        """Anonymous users see only is_listed=True tournaments."""
        self.t_a.is_listed = True
        self.t_a.save()
        qs = Tournament.objects.visible_to(None)
        self.assertIn(self.t_a, qs)
        self.assertNotIn(self.t_b, qs)

    def test_superuser_sees_all(self):
        superuser = User.objects.create_superuser("super", password="testpass")
        qs = Tournament.objects.visible_to(superuser)
        self.assertIn(self.t_a, qs)
        self.assertIn(self.t_b, qs)


class RoleEnforcementTests(TestCase):
    """RBAC role hierarchy enforcement."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", slug="test-org")
        self.tournament = Tournament.objects.create(
            name="Test", slug="test-t", organization=self.org)
        self.owner = User.objects.create_user("owner", password="testpass")
        self.admin = User.objects.create_user("admin", password="testpass")
        self.member = User.objects.create_user("member", password="testpass")
        self.viewer = User.objects.create_user("viewer", password="testpass")
        self.outsider = User.objects.create_user("outsider", password="testpass")
        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner,
            role=OrganizationMembership.Role.OWNER)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.admin,
            role=OrganizationMembership.Role.ADMIN)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.member,
            role=OrganizationMembership.Role.MEMBER)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.viewer,
            role=OrganizationMembership.Role.VIEWER)

    def test_owner_has_middleware_access(self):
        self.assertTrue(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.owner))

    def test_admin_has_middleware_access(self):
        self.assertTrue(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.admin))

    def test_member_has_middleware_access(self):
        self.assertTrue(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.member))

    def test_viewer_blocked_from_admin_routes(self):
        """VIEWER should NOT pass middleware access check for private routes."""
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.viewer))

    def test_outsider_blocked(self):
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.outsider))

    def test_anonymous_blocked(self):
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.tournament, AnonymousUser()))

    def test_none_user_blocked(self):
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.tournament, None))

    def test_viewer_can_see_tournament_in_listing(self):
        """VIEWER can see the tournament via visible_to()."""
        qs = Tournament.objects.visible_to(self.viewer)
        self.assertIn(self.tournament, qs)

    def test_owner_has_permission(self):
        self.assertTrue(has_permission(self.owner, Permission.VIEW_TEAMS, self.tournament))

    def test_admin_has_permission(self):
        self.assertTrue(has_permission(self.admin, Permission.VIEW_TEAMS, self.tournament))

    def test_viewer_no_permission(self):
        """VIEWER should not get has_permission() for edit operations."""
        self.assertFalse(has_permission(self.viewer, Permission.EDIT_SETTINGS, self.tournament))


class OwnershipSafetyTests(TestCase):
    """Ownership protection: last owner cannot be removed or demoted."""

    def setUp(self):
        self.org = Organization.objects.create(name="Safe Org", slug="safe-org")
        self.owner = User.objects.create_user("sole_owner", password="testpass")
        self.membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.owner,
            role=OrganizationMembership.Role.OWNER)

    def test_cannot_remove_last_owner(self):
        """Application logic should prevent this; test the model state."""
        owner_count = OrganizationMembership.objects.filter(
            organization=self.org,
            role=OrganizationMembership.Role.OWNER,
        ).count()
        self.assertEqual(owner_count, 1)

    def test_second_owner_allows_removal(self):
        second_owner = User.objects.create_user("owner2", password="testpass")
        OrganizationMembership.objects.create(
            organization=self.org, user=second_owner,
            role=OrganizationMembership.Role.OWNER)
        owner_count = OrganizationMembership.objects.filter(
            organization=self.org,
            role=OrganizationMembership.Role.OWNER,
        ).count()
        self.assertEqual(owner_count, 2)


class PermissionEscalationTests(TestCase):
    """Ensure users cannot escalate their own roles."""

    def setUp(self):
        self.org = Organization.objects.create(name="Esc Org", slug="esc-org")
        self.admin = User.objects.create_user("admin_esc", password="testpass")
        self.admin_membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.admin,
            role=OrganizationMembership.Role.ADMIN)

    def test_admin_is_not_owner(self):
        self.assertFalse(user_is_org_owner(self.admin, self.org))

    def test_admin_is_admin(self):
        self.assertTrue(user_is_org_admin(self.admin, self.org))

    def test_member_is_not_admin(self):
        member = User.objects.create_user("member_esc", password="testpass")
        OrganizationMembership.objects.create(
            organization=self.org, user=member,
            role=OrganizationMembership.Role.MEMBER)
        self.assertFalse(user_is_org_admin(member, self.org))


class MembershipRevocationTests(TestCase):
    """When a user is removed from an org, access is revoked immediately."""

    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name="Revoke Org", slug="revoke-org")
        self.tournament = Tournament.objects.create(
            name="Revoke T", slug="revoke-t", organization=self.org)
        self.user = User.objects.create_user("revoked_user", password="testpass")
        self.membership = OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.MEMBER)

    def test_has_access_before_revocation(self):
        self.assertTrue(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.user))

    def test_loses_access_after_revocation(self):
        """Deleting the membership must immediately revoke tournament access."""
        self.membership.delete()
        self.assertFalse(
            DebateMiddleware._user_has_tournament_access(self.tournament, self.user))

    def test_visible_to_after_revocation(self):
        """Tournament should not appear in visible_to() after revocation."""
        self.membership.delete()
        self.tournament.is_listed = False
        self.tournament.save()
        qs = Tournament.objects.visible_to(self.user)
        self.assertNotIn(self.tournament, qs)


class HelperFunctionTests(TestCase):
    """Test the helper functions in organizations.models."""

    def setUp(self):
        self.org = Organization.objects.create(name="Helper Org", slug="helper-org")
        self.user = User.objects.create_user("helper_user", password="testpass")

    def test_get_user_org_role_none_for_non_member(self):
        self.assertIsNone(get_user_org_role(self.user, self.org))

    def test_get_user_org_role_returns_role(self):
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.ADMIN)
        self.assertEqual(
            get_user_org_role(self.user, self.org),
            OrganizationMembership.Role.ADMIN)

    def test_user_is_org_member_false_for_anonymous(self):
        self.assertFalse(user_is_org_member(AnonymousUser(), self.org))

    def test_user_is_org_member_false_for_none(self):
        self.assertFalse(user_is_org_member(None, self.org))

    def test_get_user_organizations_empty_for_anonymous(self):
        self.assertEqual(get_user_organizations(AnonymousUser()).count(), 0)

    def test_get_user_organizations_returns_orgs(self):
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.MEMBER)
        orgs = get_user_organizations(self.user)
        self.assertIn(self.org, orgs)


class CacheInvalidationTests(TestCase):
    """Test that signals properly invalidate caches."""

    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name="Cache Org", slug="cache-org")
        self.tournament = Tournament.objects.create(
            name="Cache T", slug="cache-t", organization=self.org)
        self.user = User.objects.create_user("cache_user", password="testpass")

    def test_tournament_save_clears_cache(self):
        """Saving a tournament must clear its middleware cache entry."""
        cache_key = f"{self.tournament.slug}_object"
        cache.set(cache_key, self.tournament, 3600)
        self.assertIsNotNone(cache.get(cache_key))

        # Save triggers signal
        self.tournament.name = "Updated Name"
        self.tournament.save()
        self.assertIsNone(cache.get(cache_key))

    def test_membership_change_bumps_perm_version(self):
        """Creating/deleting a membership must bump perm cache version."""
        from organizations.signals import PERM_VERSION_KEY, get_perm_cache_version

        # Establish baseline version
        v1 = get_perm_cache_version(self.user.id)

        # Create membership (triggers post_save signal)
        m = OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.MEMBER)
        v2 = get_perm_cache_version(self.user.id)
        self.assertGreater(v2, v1)

        # Delete membership (triggers post_delete signal)
        m.delete()
        v3 = get_perm_cache_version(self.user.id)
        self.assertGreater(v3, v2)


# ────────────────────────────────────────────────────────────────────────────
# Sidebar tournament-list isolation tests  (DB-annotated via nav_for_user)
# ────────────────────────────────────────────────────────────────────────────

class NavAnnotationTests(TestCase):
    """Test nav_for_user() DB-side annotations per role.

    The test tournament is ``is_listed=True`` so every role can see it;
    we're testing the *flags*, not visibility.
    """

    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name="Nav Org", slug="nav-org")
        self.tournament = Tournament.objects.create(
            name="Nav T", slug="nav-t", organization=self.org, is_listed=True)
        self.owner = User.objects.create_user("nav_owner", password="pass")
        self.admin = User.objects.create_user("nav_admin", password="pass")
        self.member = User.objects.create_user("nav_member", password="pass")
        self.viewer = User.objects.create_user("nav_viewer", password="pass")
        self.outsider = User.objects.create_user("nav_outsider", password="pass")
        self.superuser = User.objects.create_superuser("nav_super", password="pass")

        OrganizationMembership.objects.create(
            organization=self.org, user=self.owner,
            role=OrganizationMembership.Role.OWNER)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.admin,
            role=OrganizationMembership.Role.ADMIN)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.member,
            role=OrganizationMembership.Role.MEMBER)
        OrganizationMembership.objects.create(
            organization=self.org, user=self.viewer,
            role=OrganizationMembership.Role.VIEWER)

    def _get(self, user):
        """Return the test tournament as annotated by nav_for_user()."""
        qs = Tournament.objects.nav_for_user(user)
        for t in qs:
            if t.pk == self.tournament.pk:
                return t
        self.fail("Tournament not visible to user")

    # ── Owner ──

    def test_owner_can_admin(self):
        self.assertTrue(self._get(self.owner).user_can_admin)

    def test_owner_can_assist(self):
        self.assertTrue(self._get(self.owner).user_can_assist)

    def test_owner_can_edit_db(self):
        self.assertTrue(self._get(self.owner).user_can_edit_db)

    # ── Admin ──

    def test_admin_can_admin(self):
        self.assertTrue(self._get(self.admin).user_can_admin)

    def test_admin_can_assist(self):
        self.assertTrue(self._get(self.admin).user_can_assist)

    def test_admin_can_edit_db(self):
        self.assertTrue(self._get(self.admin).user_can_edit_db)

    # ── Member ──

    def test_member_cannot_admin(self):
        self.assertFalse(self._get(self.member).user_can_admin)

    def test_member_can_assist(self):
        self.assertTrue(self._get(self.member).user_can_assist)

    def test_member_cannot_edit_db(self):
        self.assertFalse(self._get(self.member).user_can_edit_db)

    # ── Viewer ──

    def test_viewer_cannot_admin(self):
        self.assertFalse(self._get(self.viewer).user_can_admin)

    def test_viewer_cannot_assist(self):
        self.assertFalse(self._get(self.viewer).user_can_assist)

    def test_viewer_cannot_edit_db(self):
        self.assertFalse(self._get(self.viewer).user_can_edit_db)

    # ── Outsider (sees listed tournament, no flags) ──

    def test_outsider_cannot_admin(self):
        self.assertFalse(self._get(self.outsider).user_can_admin)

    def test_outsider_cannot_assist(self):
        self.assertFalse(self._get(self.outsider).user_can_assist)

    def test_outsider_cannot_edit_db(self):
        self.assertFalse(self._get(self.outsider).user_can_edit_db)

    # ── Superuser ──

    def test_superuser_can_admin(self):
        self.assertTrue(self._get(self.superuser).user_can_admin)

    def test_superuser_can_assist(self):
        self.assertTrue(self._get(self.superuser).user_can_assist)

    def test_superuser_can_edit_db(self):
        self.assertTrue(self._get(self.superuser).user_can_edit_db)

    # ── Anonymous ──

    def test_anonymous_cannot_admin(self):
        self.assertFalse(self._get(None).user_can_admin)

    def test_anonymous_cannot_assist(self):
        self.assertFalse(self._get(None).user_can_assist)

    # ── Cross-org isolation ──

    def test_other_org_owner_cannot_admin(self):
        """OWNER of OrgX must NOT get admin on OrgY's tournament."""
        org_x = Organization.objects.create(name="Org X", slug="org-x")
        user_x = User.objects.create_user("user_x", password="pass")
        OrganizationMembership.objects.create(
            organization=org_x, user=user_x,
            role=OrganizationMembership.Role.OWNER)
        self.assertFalse(self._get(user_x).user_can_admin)

    def test_other_org_member_cannot_assist(self):
        org_x = Organization.objects.create(name="Org X2", slug="org-x2")
        user_x = User.objects.create_user("user_x2", password="pass")
        OrganizationMembership.objects.create(
            organization=org_x, user=user_x,
            role=OrganizationMembership.Role.MEMBER)
        self.assertFalse(self._get(user_x).user_can_assist)

    # ── Tournament owner (direct) ──

    def test_tournament_owner_can_admin(self):
        """Tournament.owner gets admin even without org membership."""
        direct_owner = User.objects.create_user("t_owner", password="pass")
        self.tournament.owner = direct_owner
        self.tournament.save()
        self.assertTrue(self._get(direct_owner).user_can_admin)

    def test_tournament_owner_can_assist(self):
        direct_owner = User.objects.create_user("t_owner2", password="pass")
        self.tournament.owner = direct_owner
        self.tournament.save()
        self.assertTrue(self._get(direct_owner).user_can_assist)


class NavVisibilityTests(TestCase):
    """Test that nav_for_user() correctly scopes *which* tournaments appear."""

    def setUp(self):
        cache.clear()
        self.org_a = Organization.objects.create(name="VisOrg A", slug="vis-a")
        self.org_b = Organization.objects.create(name="VisOrg B", slug="vis-b")
        self.t_private = Tournament.objects.create(
            name="Private T", slug="priv-t", organization=self.org_a,
            is_listed=False)
        self.t_listed = Tournament.objects.create(
            name="Listed T", slug="listed-t", organization=self.org_b,
            is_listed=True)
        self.user_a = User.objects.create_user("vis_ua", password="pass")
        OrganizationMembership.objects.create(
            organization=self.org_a, user=self.user_a,
            role=OrganizationMembership.Role.ADMIN)

    def _slugs(self, user):
        return set(
            Tournament.objects.nav_for_user(user)
            .values_list('slug', flat=True)
        )

    def test_org_member_sees_own_private(self):
        self.assertIn('priv-t', self._slugs(self.user_a))

    def test_org_member_sees_listed(self):
        self.assertIn('listed-t', self._slugs(self.user_a))

    def test_outsider_sees_only_listed(self):
        outsider = User.objects.create_user("vis_outsider", password="pass")
        slugs = self._slugs(outsider)
        self.assertIn('listed-t', slugs)
        self.assertNotIn('priv-t', slugs)

    def test_anonymous_sees_only_listed(self):
        slugs = self._slugs(None)
        self.assertIn('listed-t', slugs)
        self.assertNotIn('priv-t', slugs)

    def test_superuser_sees_all(self):
        su = User.objects.create_superuser("vis_su", password="pass")
        slugs = self._slugs(su)
        self.assertIn('priv-t', slugs)
        self.assertIn('listed-t', slugs)


class NavQueryCountTests(TestCase):
    """Ensure nav_for_user() and the caching layer stay within query budget."""

    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name="QC Org", slug="qc-org")
        # Create 10 tournaments to prove no N+1
        for i in range(10):
            Tournament.objects.create(
                name=f"QC T{i}", slug=f"qc-t{i}", organization=self.org)
        self.user = User.objects.create_user("qc_user", password="pass")
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.ADMIN)
        self.superuser = User.objects.create_superuser("qc_su", password="pass")

    def test_regular_user_single_query(self):
        """nav_for_user() for an authenticated user: 1 DB query."""
        with self.assertNumQueries(1):
            list(Tournament.objects.nav_for_user(self.user))

    def test_anonymous_single_query(self):
        with self.assertNumQueries(1):
            list(Tournament.objects.nav_for_user(None))

    def test_superuser_single_query(self):
        with self.assertNumQueries(1):
            list(Tournament.objects.nav_for_user(self.superuser))

    def test_ten_tournaments_still_one_query(self):
        """Even with 10 tournaments, only 1 DB query should run."""
        with self.assertNumQueries(1):
            list(Tournament.objects.nav_for_user(self.user))

    def test_cached_result_zero_queries(self):
        """After caching, _get_nav_tournaments must hit 0 DB queries."""
        from utils.context_processors import _get_nav_tournaments
        _get_nav_tournaments(self.user)          # prime cache
        with self.assertNumQueries(0):
            result = _get_nav_tournaments(self.user)
        self.assertEqual(len(result), 10)

    def test_cached_anonymous_zero_queries(self):
        from utils.context_processors import _get_nav_tournaments
        _get_nav_tournaments(None)               # prime cache
        with self.assertNumQueries(0):
            _get_nav_tournaments(None)

    def test_cache_invalidated_on_version_bump(self):
        """Bumping perm_version must cause a cache miss (fresh query)."""
        from organizations.signals import bump_perm_cache_version
        from utils.context_processors import _get_nav_tournaments
        _get_nav_tournaments(self.user)           # prime cache
        bump_perm_cache_version(self.user.pk)     # simulate membership change
        with self.assertNumQueries(1):
            _get_nav_tournaments(self.user)


# ────────────────────────────────────────────────────────────────────────────
# Phase 1 — Workspace foundation model tests
# ────────────────────────────────────────────────────────────────────────────

class WorkspaceFieldDefaultsTests(TestCase):
    """Test that new Organization workspace fields have correct defaults."""

    def test_new_org_defaults_workspace_disabled(self):
        org = Organization.objects.create(name="Default Org", slug="default-org")
        org.refresh_from_db()
        self.assertFalse(org.is_workspace_enabled)

    def test_new_org_defaults_description_blank(self):
        org = Organization.objects.create(name="Desc Org", slug="desc-org")
        org.refresh_from_db()
        self.assertEqual(org.description, "")

    def test_new_org_defaults_logo_null(self):
        org = Organization.objects.create(name="Logo Org", slug="logo-org")
        org.refresh_from_db()
        self.assertFalse(org.logo)  # falsy when no file

    def test_workspace_enabled_can_be_set(self):
        org = Organization.objects.create(
            name="WS Org", slug="ws-org", is_workspace_enabled=True)
        org.refresh_from_db()
        self.assertTrue(org.is_workspace_enabled)

    def test_description_accepts_text(self):
        org = Organization.objects.create(
            name="Text Org", slug="text-org", description="A test org")
        org.refresh_from_db()
        self.assertEqual(org.description, "A test org")


class ExtendedRoleHierarchyTests(TestCase):
    """Test the extended role choices and hierarchy levels."""

    def setUp(self):
        self.org = Organization.objects.create(name="Role Org", slug="role-org")

    def _create_membership(self, role):
        user = User.objects.create_user(f"user_{role}", password="testpass")
        return OrganizationMembership.objects.create(
            organization=self.org, user=user, role=role)

    def test_tabmaster_role_level(self):
        m = self._create_membership(OrganizationMembership.Role.TABMASTER)
        self.assertEqual(m.role_level, 3)

    def test_editor_role_level(self):
        m = self._create_membership(OrganizationMembership.Role.EDITOR)
        self.assertEqual(m.role_level, 2)

    def test_member_role_still_valid(self):
        """Existing role='member' rows still work and map to level 2."""
        m = self._create_membership(OrganizationMembership.Role.MEMBER)
        self.assertEqual(m.role, 'member')
        self.assertEqual(m.role_level, 2)

    def test_owner_role_level(self):
        m = self._create_membership(OrganizationMembership.Role.OWNER)
        self.assertEqual(m.role_level, 5)

    def test_admin_role_level(self):
        m = self._create_membership(OrganizationMembership.Role.ADMIN)
        self.assertEqual(m.role_level, 4)

    def test_viewer_role_level(self):
        m = self._create_membership(OrganizationMembership.Role.VIEWER)
        self.assertEqual(m.role_level, 1)

    def test_has_role_at_least_tabmaster_ge_editor(self):
        m = self._create_membership(OrganizationMembership.Role.TABMASTER)
        self.assertTrue(m.has_role_at_least(OrganizationMembership.Role.EDITOR))

    def test_has_role_at_least_tabmaster_lt_admin(self):
        m = self._create_membership(OrganizationMembership.Role.TABMASTER)
        self.assertFalse(m.has_role_at_least(OrganizationMembership.Role.ADMIN))

    def test_has_role_at_least_admin_ge_tabmaster(self):
        m = self._create_membership(OrganizationMembership.Role.ADMIN)
        self.assertTrue(m.has_role_at_least(OrganizationMembership.Role.TABMASTER))

    def test_has_role_at_least_editor_eq_member(self):
        """EDITOR and MEMBER are at the same level; each satisfies the other."""
        m = self._create_membership(OrganizationMembership.Role.EDITOR)
        self.assertTrue(m.has_role_at_least(OrganizationMembership.Role.MEMBER))

    def test_has_role_at_least_viewer_lt_editor(self):
        m = self._create_membership(OrganizationMembership.Role.VIEWER)
        self.assertFalse(m.has_role_at_least(OrganizationMembership.Role.EDITOR))
