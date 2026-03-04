"""Tests for the 'Edit Database' link visibility and admin-site access.

Covers:
- Template context flag ``user_can_edit_db``
- Custom ``NekoTabAdminSite.has_permission()``
- Custom ``TournamentAdminBackend`` granting model-level perms
- Role matrix: superuser, tournament owner, org OWNER, org ADMIN,
  org MEMBER, org VIEWER, and outsider
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from organizations.models import Organization, OrganizationMembership
from tournaments.models import Tournament
from utils.admin_site import (
    NekoTabAdminSite,
    TournamentAdminBackend,
    TOURNAMENT_ADMIN_APP_LABELS,
    _user_can_admin_any_tournament,
)
from utils.context_processors import _get_nav_tournaments

User = get_user_model()


class EditDatabaseSetupMixin:
    """Common setUp for Edit Database tests."""

    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name="Test Org", slug="edit-db-org")
        self.tournament = Tournament.objects.create(
            name="Test T", slug="edit-db-t", organization=self.org,
        )
        self.superuser = User.objects.create_superuser(
            "su", email="su@test.com", password="testpass",
        )
        self.owner = User.objects.create_user("t_owner", password="testpass")
        self.tournament.owner = self.owner
        self.tournament.save()

        self.org_owner = User.objects.create_user("org_owner", password="testpass")
        self.org_admin = User.objects.create_user("org_admin", password="testpass")
        self.org_member = User.objects.create_user("org_member", password="testpass")
        self.org_viewer = User.objects.create_user("org_viewer", password="testpass")
        self.outsider = User.objects.create_user("outsider", password="testpass")

        OrganizationMembership.objects.create(
            organization=self.org, user=self.org_owner,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.org_admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.org_member,
            role=OrganizationMembership.Role.MEMBER,
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.org_viewer,
            role=OrganizationMembership.Role.VIEWER,
        )


# ── NavTournament context flag ──────────────────────────────────────────

class UserCanEditDbContextTests(EditDatabaseSetupMixin, TestCase):
    """``user_can_edit_db`` annotation on NavTournament objects."""

    def _flag_for(self, user):
        cache.clear()  # Ensure fresh query
        nav = _get_nav_tournaments(user)
        return any(t.user_can_edit_db for t in nav)

    def test_superuser_flag(self):
        self.assertTrue(self._flag_for(self.superuser))

    def test_tournament_owner_flag(self):
        self.assertTrue(self._flag_for(self.owner))

    def test_org_owner_flag(self):
        self.assertTrue(self._flag_for(self.org_owner))

    def test_org_admin_flag(self):
        self.assertTrue(self._flag_for(self.org_admin))

    def test_org_member_no_flag(self):
        self.assertFalse(self._flag_for(self.org_member))

    def test_org_viewer_no_flag(self):
        self.assertFalse(self._flag_for(self.org_viewer))

    def test_outsider_no_flag(self):
        self.assertFalse(self._flag_for(self.outsider))

    def test_anonymous_no_flag(self):
        self.assertFalse(self._flag_for(AnonymousUser()))


# ── AdminSite.has_permission() ──────────────────────────────────────────

class AdminSiteHasPermissionTests(EditDatabaseSetupMixin, TestCase):
    """``NekoTabAdminSite.has_permission()`` lets qualifying users through."""

    def setUp(self):
        super().setUp()
        self.site = NekoTabAdminSite(name='test_admin')
        self.factory = RequestFactory()

    def _has_perm(self, user):
        request = self.factory.get('/database/')
        request.user = user
        return self.site.has_permission(request)

    def test_superuser_allowed(self):
        self.assertTrue(self._has_perm(self.superuser))

    def test_staff_user_allowed(self):
        staff = User.objects.create_user("staff", password="testpass", is_staff=True)
        self.assertTrue(self._has_perm(staff))

    def test_tournament_owner_allowed(self):
        self.assertTrue(self._has_perm(self.owner))

    def test_org_owner_allowed(self):
        self.assertTrue(self._has_perm(self.org_owner))

    def test_org_admin_allowed(self):
        self.assertTrue(self._has_perm(self.org_admin))

    def test_org_member_denied(self):
        self.assertFalse(self._has_perm(self.org_member))

    def test_org_viewer_denied(self):
        self.assertFalse(self._has_perm(self.org_viewer))

    def test_outsider_denied(self):
        self.assertFalse(self._has_perm(self.outsider))

    def test_anonymous_denied(self):
        self.assertFalse(self._has_perm(AnonymousUser()))

    def test_inactive_user_denied(self):
        inactive = User.objects.create_user("inactive", password="testpass", is_active=False)
        self.tournament.owner = inactive
        self.tournament.save()
        self.assertFalse(self._has_perm(inactive))


# ── TournamentAdminBackend ──────────────────────────────────────────────

class TournamentAdminBackendTests(EditDatabaseSetupMixin, TestCase):
    """Custom auth backend grants model-level perms to tournament admins."""

    def setUp(self):
        super().setUp()
        self.backend = TournamentAdminBackend()

    # ── has_module_perms ────────────────────────────────────────────────

    def test_owner_has_module_perms_tournaments(self):
        self.assertTrue(self.backend.has_module_perms(self.owner, 'tournaments'))

    def test_org_admin_has_module_perms_participants(self):
        self.assertTrue(self.backend.has_module_perms(self.org_admin, 'participants'))

    def test_member_no_module_perms(self):
        self.assertFalse(self.backend.has_module_perms(self.org_member, 'tournaments'))

    def test_outsider_no_module_perms(self):
        self.assertFalse(self.backend.has_module_perms(self.outsider, 'tournaments'))

    def test_restricted_app_label_denied(self):
        """Even qualifying users cannot access non-tournament app labels."""
        self.assertFalse(self.backend.has_module_perms(self.owner, 'auth'))
        self.assertFalse(self.backend.has_module_perms(self.owner, 'sessions'))

    # ── has_perm ────────────────────────────────────────────────────────

    def test_owner_has_perm_change_tournament(self):
        self.assertTrue(self.backend.has_perm(self.owner, 'tournaments.change_tournament'))

    def test_org_owner_has_perm_view_venue(self):
        self.assertTrue(self.backend.has_perm(self.org_owner, 'venues.view_venue'))

    def test_member_no_perm(self):
        self.assertFalse(self.backend.has_perm(self.org_member, 'tournaments.change_tournament'))

    def test_restricted_perm_denied(self):
        """Permissions for restricted apps always denied by this backend."""
        self.assertFalse(self.backend.has_perm(self.owner, 'auth.change_user'))

    # ── authenticate ────────────────────────────────────────────────────

    def test_authenticate_returns_none(self):
        self.assertIsNone(self.backend.authenticate(request=None))


# ── _user_can_admin_any_tournament helper ───────────────────────────────

class UserCanAdminAnyTournamentTests(EditDatabaseSetupMixin, TestCase):
    """Direct tests for the ``_user_can_admin_any_tournament()`` helper."""

    def test_tournament_owner(self):
        self.assertTrue(_user_can_admin_any_tournament(self.owner))

    def test_org_owner(self):
        self.assertTrue(_user_can_admin_any_tournament(self.org_owner))

    def test_org_admin(self):
        self.assertTrue(_user_can_admin_any_tournament(self.org_admin))

    def test_org_member(self):
        self.assertFalse(_user_can_admin_any_tournament(self.org_member))

    def test_outsider(self):
        self.assertFalse(_user_can_admin_any_tournament(self.outsider))

    def test_caching(self):
        """Result is cached on the user object."""
        _user_can_admin_any_tournament(self.owner)
        self.assertTrue(hasattr(self.owner, '_nekotab_can_admin_any'))
        self.assertTrue(self.owner._nekotab_can_admin_any)


# ── Integration: /database/ route ───────────────────────────────────────

NO_PERM_MSG = "permission to view or edit"


@override_settings(
    AUTHENTICATION_BACKENDS=[
        'utils.admin_site.TournamentAdminBackend',
        'django.contrib.auth.backends.ModelBackend',
    ],
)
class AdminRouteAccessTests(EditDatabaseSetupMixin, TestCase):
    """Integration tests hitting /database/ via the test client."""

    def _login_and_get(self, user):
        self.client.force_login(user)
        return self.client.get('/database/', follow=True)

    # ── Superuser ───────────────────────────────────────────────────────

    def test_superuser_can_access(self):
        resp = self._login_and_get(self.superuser)
        self.assertEqual(resp.status_code, 200)

    def test_superuser_sees_models(self):
        resp = self._login_and_get(self.superuser)
        content = resp.content.decode().lower()
        self.assertNotIn(NO_PERM_MSG, content)
        self.assertIn('participants', content)

    # ── Tournament owner ────────────────────────────────────────────────

    def test_tournament_owner_can_access(self):
        resp = self._login_and_get(self.owner)
        self.assertEqual(resp.status_code, 200)

    def test_tournament_owner_sees_models(self):
        """Owner should see allowed app sections and NOT the no-permission message."""
        resp = self._login_and_get(self.owner)
        content = resp.content.decode().lower()
        self.assertNotIn(NO_PERM_MSG, content)
        # Should see at least some whitelisted app sections
        self.assertIn('participants', content)
        self.assertIn('tournaments', content)

    def test_tournament_owner_cannot_see_auth(self):
        """Owner must NOT see sensitive app labels like auth."""
        resp = self._login_and_get(self.owner)
        # Look for the auth app section heading (not just the word "auth" anywhere)
        content = resp.content.decode()
        # Django admin renders app labels as section links like /database/auth/
        self.assertNotIn('/database/auth/', content)

    # ── Org OWNER ───────────────────────────────────────────────────────

    def test_org_owner_can_access(self):
        resp = self._login_and_get(self.org_owner)
        self.assertEqual(resp.status_code, 200)

    def test_org_owner_sees_models(self):
        resp = self._login_and_get(self.org_owner)
        content = resp.content.decode().lower()
        self.assertNotIn(NO_PERM_MSG, content)
        self.assertIn('participants', content)

    # ── Org ADMIN ───────────────────────────────────────────────────────

    def test_org_admin_can_access(self):
        resp = self._login_and_get(self.org_admin)
        self.assertEqual(resp.status_code, 200)

    def test_org_admin_sees_models(self):
        resp = self._login_and_get(self.org_admin)
        content = resp.content.decode().lower()
        self.assertNotIn(NO_PERM_MSG, content)
        self.assertIn('venues', content)

    # ── Denied roles ────────────────────────────────────────────────────

    def test_outsider_redirected(self):
        resp = self._login_and_get(self.outsider)
        # Should be redirected to admin login page
        self.assertIn('/database/login/', resp.redirect_chain[-1][0])

    def test_org_member_redirected(self):
        resp = self._login_and_get(self.org_member)
        self.assertIn('/database/login/', resp.redirect_chain[-1][0])

    def test_org_viewer_redirected(self):
        resp = self._login_and_get(self.org_viewer)
        self.assertIn('/database/login/', resp.redirect_chain[-1][0])

    def test_anonymous_redirected(self):
        resp = self.client.get('/database/', follow=True)
        self.assertIn('/database/login/', resp.redirect_chain[-1][0])
