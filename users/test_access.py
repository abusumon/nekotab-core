"""Tournament roles: Tab Directors get full access, invites need full access,
removing a role takes effect immediately."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from organizations.models import Organization
from tournaments.models import Tournament, TournamentStaffMembership

from .groups import ensure_role_groups, tab_director_group_names
from .models import Group, Membership
from .permissions import Permission, has_full_access, has_permission

User = get_user_model()


class AccessTests(TestCase):

    def setUp(self):
        cache.clear()
        from unittest import mock
        try:  # NekoTab's paywall would redirect unpaid tournaments' admin pages
            patcher = mock.patch('donations.premium.premium_enabled', return_value=False)
            patcher.start()
            self.addCleanup(patcher.stop)
        except ModuleNotFoundError:
            pass
        self.owner = User.objects.create_user('owner', 'o@example.com', 'pw-owner-1')
        org = Organization.objects.create(name='Org', slug='org-access')
        self.t = Tournament.objects.create(name='Access Open', short_name='AO', slug='access-open',
                                           owner=self.owner, organization=org)
        from tournaments.models import Round
        Round.objects.create(tournament=self.t, seq=1, name='Round 1', abbreviation='R1')
        ensure_role_groups(self.t)
        self.td_group = Group.objects.get(tournament=self.t, name__in=tab_director_group_names())
        self.equity_group = Group.objects.get(tournament=self.t, name='Equity')
        self.td = User.objects.create_user('td', 'td@example.com', 'pw-td-1')
        self.eq = User.objects.create_user('eq', 'eq@example.com', 'pw-eq-1')
        Membership.objects.create(user=self.td, group=self.td_group)
        Membership.objects.create(user=self.eq, group=self.equity_group)

    def fresh(self, user):
        return User.objects.get(pk=user.pk)  # drops per-request memo

    def test_tab_director_has_permissions_missing_from_old_snapshot(self):
        # Simulate a group created before a permission existed.
        self.td_group.permissions = [Permission.VIEW_TEAMS]
        self.td_group.save()
        self.assertTrue(has_permission(self.fresh(self.td), Permission.EDIT_MOTION, self.t))
        self.assertTrue(has_full_access(self.fresh(self.td), self.t))

    def test_equity_is_limited(self):
        eq = self.fresh(self.eq)
        self.assertTrue(has_permission(eq, Permission.EDIT_ADJ_TEAM_CONFLICTS, self.t))
        self.assertFalse(has_permission(eq, Permission.EDIT_MOTION, self.t))
        self.assertFalse(has_full_access(eq, self.t))

    def test_staff_membership_tab_director(self):
        u = User.objects.create_user('sm', 'sm@example.com', 'pw-sm-1')
        TournamentStaffMembership.objects.create(tournament=self.t, user=u,
                                                 role=TournamentStaffMembership.Role.TAB_DIRECTOR)
        self.assertTrue(has_full_access(self.fresh(u), self.t))
        self.client.force_login(u)
        self.assertEqual(self.client.get('/access-open/admin/users/invite/').status_code, 200)

    def test_unpermissioned_admin_page_open_to_tab_director_not_equity(self):
        self.client.force_login(self.td)
        self.assertNotEqual(self.client.get('/access-open/admin/fix-debate-teams/').status_code, 403)
        self.client.force_login(self.eq)
        self.assertIn(self.client.get('/access-open/admin/fix-debate-teams/').status_code, (302, 403))

    def test_invite_page_needs_full_access(self):
        for user, ok in ((self.owner, True), (self.td, True), (self.eq, False)):
            self.client.force_login(user)
            r = self.client.get('/access-open/admin/users/invite/')
            self.assertEqual(r.status_code == 200, ok, (user, r.status_code, r.get('Location')))
        self.client.force_login(self.owner)
        r = self.client.get('/access-open/admin/users/invite/')
        self.assertContains(r, 'Full access')
        self.assertContains(r, 'People with access')
        self.assertContains(r, 'td@example.com')

    def test_invite_existing_user_then_remove(self):
        new = User.objects.create_user('helper', 'helper@example.com', 'pw-helper-1')
        self.client.force_login(self.owner)
        r = self.client.post('/access-open/admin/users/invite/',
                             {'email': 'HELPER@example.com', 'role': self.td_group.pk})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(has_full_access(self.fresh(new), self.t))
        m = Membership.objects.get(user=new, group=self.td_group)
        r = self.client.post('/access-open/admin/users/access/remove/', {'kind': 'role', 'pk': m.pk})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Membership.objects.filter(pk=m.pk).exists())
        # Cached decisions are invalidated, so access is gone immediately.
        self.assertFalse(has_full_access(self.fresh(new), self.t))
        self.assertFalse(has_permission(self.fresh(new), Permission.EDIT_MOTION, self.t))

    def test_equity_cannot_remove_roles(self):
        m = Membership.objects.get(user=self.td)
        self.client.force_login(self.eq)
        self.client.post('/access-open/admin/users/access/remove/', {'kind': 'role', 'pk': m.pk})
        self.assertTrue(Membership.objects.filter(pk=m.pk).exists())

    def test_top_up_adds_missing_permissions(self):
        self.equity_group.permissions = []
        self.equity_group.save()
        ensure_role_groups(self.t)
        self.equity_group.refresh_from_db()
        self.assertIn(Permission.EDIT_ADJ_TEAM_CONFLICTS, self.equity_group.permissions)
