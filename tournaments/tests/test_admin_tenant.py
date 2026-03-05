"""Tests for multi-tenant admin isolation (/database/).

Verifies that non-superuser administrators can only see and edit
tournaments (and related objects) that they own or admin via their
organisation membership.
"""

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings

from organizations.models import Organization, OrganizationMembership
from tournaments.models import Round, Tournament
from participants.models import Team
from users.models import UserPermission


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class AdminTenantIsolationTests(TestCase):
    """Integration tests for /database/ tenant isolation."""

    @classmethod
    def setUpTestData(cls):
        # ── Organisations ───────────────────────────────────────────────
        cls.org_a = Organization.objects.create(name="Org A", slug="org-a")
        cls.org_b = Organization.objects.create(name="Org B", slug="org-b")

        # ── Users ───────────────────────────────────────────────────────
        cls.superuser = User.objects.create_superuser(
            'superadmin', 'super@test.com', 'pw',
        )
        # owner_a: owns tournament_a1 AND is OWNER of org_a
        cls.owner_a = User.objects.create_user('owner_a', 'ownera@test.com', 'pw')
        OrganizationMembership.objects.create(
            organization=cls.org_a, user=cls.owner_a,
            role=OrganizationMembership.Role.OWNER,
        )

        # admin_a: ADMIN of org_a (should see org_a tournaments)
        cls.admin_a = User.objects.create_user('admin_a', 'admina@test.com', 'pw')
        OrganizationMembership.objects.create(
            organization=cls.org_a, user=cls.admin_a,
            role=OrganizationMembership.Role.ADMIN,
        )

        # owner_b: OWNER of org_b
        cls.owner_b = User.objects.create_user('owner_b', 'ownerb@test.com', 'pw')
        OrganizationMembership.objects.create(
            organization=cls.org_b, user=cls.owner_b,
            role=OrganizationMembership.Role.OWNER,
        )

        # outsider: MEMBER of org_a (should NOT have admin access unless
        # they have direct UserPermission)
        cls.outsider = User.objects.create_user('outsider', 'out@test.com', 'pw')
        OrganizationMembership.objects.create(
            organization=cls.org_a, user=cls.outsider,
            role=OrganizationMembership.Role.MEMBER,
        )

        # perm_user: has explicit permission on tournament_b1
        cls.perm_user = User.objects.create_user('perm_user', 'perm@test.com', 'pw')
        # Give perm_user ADMIN role in org_a so they can access admin
        OrganizationMembership.objects.create(
            organization=cls.org_a, user=cls.perm_user,
            role=OrganizationMembership.Role.ADMIN,
        )

        # ── Tournaments ────────────────────────────────────────────────
        cls.tournament_a1 = Tournament.objects.create(
            slug='tourney-a1', name='Tournament A1', active=True,
            owner=cls.owner_a, organization=cls.org_a,
        )
        cls.tournament_a2 = Tournament.objects.create(
            slug='tourney-a2', name='Tournament A2', active=True,
            organization=cls.org_a,
        )
        cls.tournament_b1 = Tournament.objects.create(
            slug='tourney-b1', name='Tournament B1', active=True,
            owner=cls.owner_b, organization=cls.org_b,
        )

        # ── Explicit permission ─────────────────────────────────────────
        # Use bulk_create to bypass UserPermission.save() cache key issue
        UserPermission.objects.bulk_create([
            UserPermission(
                user=cls.perm_user,
                tournament=cls.tournament_b1,
                permission='view.team',
            ),
        ])

        # ── Related objects (teams) ─────────────────────────────────────
        cls.team_a1 = Team.objects.create(
            reference='Team A1',
            use_institution_prefix=False,
            tournament=cls.tournament_a1,
        )
        cls.team_b1 = Team.objects.create(
            reference='Team B1',
            use_institution_prefix=False,
            tournament=cls.tournament_b1,
        )

        # ── Rounds ──────────────────────────────────────────────────────
        cls.round_a1 = Round.objects.create(
            tournament=cls.tournament_a1, seq=1,
            abbreviation='R1', name='Round 1',
        )
        cls.round_b1 = Round.objects.create(
            tournament=cls.tournament_b1, seq=1,
            abbreviation='R1', name='Round 1',
        )

    # ── Helper ──────────────────────────────────────────────────────────

    def _login(self, user):
        client = Client()
        client.force_login(user)
        return client

    # ════════════════════════════════════════════════════════════════════
    #  1) Tournament changelist — owner sees only their tournaments
    # ════════════════════════════════════════════════════════════════════

    def test_owner_a_sees_only_org_a_tournaments(self):
        client = self._login(self.owner_a)
        resp = client.get('/database/tournaments/tournament/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('tourney-a1', content)
        self.assertIn('tourney-a2', content)
        self.assertNotIn('tourney-b1', content)

    def test_owner_b_sees_only_org_b_tournaments(self):
        client = self._login(self.owner_b)
        resp = client.get('/database/tournaments/tournament/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertNotIn('tourney-a1', content)
        self.assertNotIn('tourney-a2', content)
        self.assertIn('tourney-b1', content)

    # ════════════════════════════════════════════════════════════════════
    #  2) Direct URL to another user's tournament → 302 (permission denied)
    # ════════════════════════════════════════════════════════════════════

    def test_owner_a_cannot_change_tournament_b1(self):
        client = self._login(self.owner_a)
        url = f'/database/tournaments/tournament/{self.tournament_b1.pk}/change/'
        resp = client.get(url)
        # Django admin returns 302 redirect to login when permission denied,
        # or 403. Either way, not 200.
        self.assertNotEqual(resp.status_code, 200)

    def test_owner_b_cannot_change_tournament_a1(self):
        client = self._login(self.owner_b)
        url = f'/database/tournaments/tournament/{self.tournament_a1.pk}/change/'
        resp = client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    # ════════════════════════════════════════════════════════════════════
    #  3) Org ADMIN sees tournaments in org but not outside
    # ════════════════════════════════════════════════════════════════════

    def test_admin_a_sees_org_a_tournaments(self):
        client = self._login(self.admin_a)
        resp = client.get('/database/tournaments/tournament/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('tourney-a1', content)
        self.assertIn('tourney-a2', content)
        self.assertNotIn('tourney-b1', content)

    def test_admin_a_cannot_change_tournament_b1(self):
        client = self._login(self.admin_a)
        url = f'/database/tournaments/tournament/{self.tournament_b1.pk}/change/'
        resp = client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    # ════════════════════════════════════════════════════════════════════
    #  4) Outsider (MEMBER role) cannot see any tournaments in admin
    # ════════════════════════════════════════════════════════════════════

    def test_outsider_no_admin_access(self):
        """MEMBER-role users without ownership or ADMIN privilege get
        denied from the admin entirely (NekoTabAdminSite.has_permission)."""
        client = self._login(self.outsider)
        resp = client.get('/database/tournaments/tournament/')
        # Should be redirected to login (302) since they can't access admin
        self.assertNotEqual(resp.status_code, 200)

    # ════════════════════════════════════════════════════════════════════
    #  5) Superuser sees all tournaments
    # ════════════════════════════════════════════════════════════════════

    def test_superuser_sees_all(self):
        client = self._login(self.superuser)
        resp = client.get('/database/tournaments/tournament/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('tourney-a1', content)
        self.assertIn('tourney-a2', content)
        self.assertIn('tourney-b1', content)

    # ════════════════════════════════════════════════════════════════════
    #  6) Related model isolation — teams
    # ════════════════════════════════════════════════════════════════════

    def test_owner_a_sees_only_own_teams(self):
        client = self._login(self.owner_a)
        resp = client.get('/database/participants/team/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Team A1', content)
        self.assertNotIn('Team B1', content)

    def test_owner_b_sees_only_own_teams(self):
        client = self._login(self.owner_b)
        resp = client.get('/database/participants/team/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertNotIn('Team A1', content)
        self.assertIn('Team B1', content)

    def test_superuser_sees_all_teams(self):
        client = self._login(self.superuser)
        resp = client.get('/database/participants/team/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Team A1', content)
        self.assertIn('Team B1', content)

    # ════════════════════════════════════════════════════════════════════
    #  7) Related model isolation — rounds
    # ════════════════════════════════════════════════════════════════════

    def test_owner_a_sees_only_own_rounds(self):
        client = self._login(self.owner_a)
        resp = client.get('/database/tournaments/round/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # Round list shows tournament name in the 'tournament' column
        self.assertIn('Tournament A1', content)
        self.assertNotIn('Tournament B1', content)

    def test_owner_a_cannot_change_round_b1(self):
        client = self._login(self.owner_a)
        url = f'/database/tournaments/round/{self.round_b1.pk}/change/'
        resp = client.get(url)
        self.assertNotEqual(resp.status_code, 200)

    # ════════════════════════════════════════════════════════════════════
    #  8) Explicit permission grants access to specific tournament
    # ════════════════════════════════════════════════════════════════════

    def test_perm_user_sees_permitted_tournament(self):
        """User with explicit UserPermission on tournament_b1 should see it
        in addition to their org_a tournaments."""
        client = self._login(self.perm_user)
        resp = client.get('/database/tournaments/tournament/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # org_a tournaments (via ADMIN role)
        self.assertIn('tourney-a1', content)
        self.assertIn('tourney-a2', content)
        # tournament_b1 (via explicit UserPermission)
        self.assertIn('tourney-b1', content)

    # ════════════════════════════════════════════════════════════════════
    #  9) Organization admin isolation
    # ════════════════════════════════════════════════════════════════════

    def test_owner_a_sees_only_own_org(self):
        client = self._login(self.owner_a)
        resp = client.get('/database/organizations/organization/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Org A', content)
        self.assertNotIn('Org B', content)

    def test_owner_b_sees_only_own_org(self):
        client = self._login(self.owner_b)
        resp = client.get('/database/organizations/organization/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertNotIn('Org A', content)
        self.assertIn('Org B', content)

    def test_superuser_sees_all_orgs(self):
        client = self._login(self.superuser)
        resp = client.get('/database/organizations/organization/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Org A', content)
        self.assertIn('Org B', content)


class GetAdminTournamentsHelperTests(TestCase):
    """Unit tests for ``get_admin_tournaments_for_user()``."""

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Test Org", slug="test-org")
        cls.other_org = Organization.objects.create(name="Other Org", slug="other-org")

        cls.superuser = User.objects.create_superuser('su', 's@t.com', 'pw')
        cls.owner = User.objects.create_user('owner', 'o@t.com', 'pw')
        cls.admin = User.objects.create_user('admin', 'a@t.com', 'pw')
        cls.member = User.objects.create_user('member', 'm@t.com', 'pw')
        cls.nobody = User.objects.create_user('nobody', 'n@t.com', 'pw')

        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.owner,
            role=OrganizationMembership.Role.OWNER,
        )
        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.admin,
            role=OrganizationMembership.Role.ADMIN,
        )
        OrganizationMembership.objects.create(
            organization=cls.org, user=cls.member,
            role=OrganizationMembership.Role.MEMBER,
        )

        cls.t_owned = Tournament.objects.create(
            slug='t-owned', name='Owned', owner=cls.owner, organization=cls.org,
        )
        cls.t_org = Tournament.objects.create(
            slug='t-org', name='Org Tournament', organization=cls.org,
        )
        cls.t_other = Tournament.objects.create(
            slug='t-other', name='Other', organization=cls.other_org,
        )

        # Give member explicit permission on t_other
        # Use bulk_create to bypass UserPermission.save() cache key issue
        UserPermission.objects.bulk_create([
            UserPermission(
                user=cls.member, tournament=cls.t_other, permission='view.team',
            ),
        ])

    def test_superuser_sees_all(self):
        from utils.admin_tenant import get_admin_tournaments_for_user
        qs = get_admin_tournaments_for_user(self.superuser)
        self.assertEqual(set(qs), {self.t_owned, self.t_org, self.t_other})

    def test_owner_sees_org_tournaments(self):
        from utils.admin_tenant import get_admin_tournaments_for_user
        qs = get_admin_tournaments_for_user(self.owner)
        self.assertIn(self.t_owned, qs)
        self.assertIn(self.t_org, qs)
        self.assertNotIn(self.t_other, qs)

    def test_admin_sees_org_tournaments(self):
        from utils.admin_tenant import get_admin_tournaments_for_user
        qs = get_admin_tournaments_for_user(self.admin)
        self.assertIn(self.t_owned, qs)
        self.assertIn(self.t_org, qs)
        self.assertNotIn(self.t_other, qs)

    def test_member_sees_only_explicitly_permitted(self):
        """MEMBER role does NOT grant admin access; only explicit
        UserPermission entries grant access."""
        from utils.admin_tenant import get_admin_tournaments_for_user
        qs = get_admin_tournaments_for_user(self.member)
        # member has explicit permission on t_other
        self.assertIn(self.t_other, qs)
        # member does NOT have OWNER/ADMIN role, so no org tournaments
        self.assertNotIn(self.t_owned, qs)
        self.assertNotIn(self.t_org, qs)

    def test_nobody_sees_nothing(self):
        from utils.admin_tenant import get_admin_tournaments_for_user
        qs = get_admin_tournaments_for_user(self.nobody)
        self.assertEqual(qs.count(), 0)
