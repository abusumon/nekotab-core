"""Tests for tenant-isolated tournament visibility (Part 1).

Verifies that ``TournamentQuerySet.visible_to()`` returns the correct
tournaments for different user types and that the middleware blocks
unauthorized access with a 404.
"""

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory

from tournaments.models import Tournament
from users.models import Group, Membership, UserPermission


class VisibleToTestCase(TestCase):
    """Unit tests for ``Tournament.objects.visible_to(user)``."""

    def setUp(self):
        # Users -----------------------------------------------------------
        self.owner = User.objects.create_user('owner', 'owner@test.com', 'pw')
        self.perm_user = User.objects.create_user('perm', 'perm@test.com', 'pw')
        self.member_user = User.objects.create_user('member', 'member@test.com', 'pw')
        self.stranger = User.objects.create_user('stranger', 'stranger@test.com', 'pw')
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', 'pw')

        # Tournaments -----------------------------------------------------
        self.owned_t = Tournament.objects.create(
            slug='owned', name='Owned', active=True, owner=self.owner,
        )
        self.shared_perm_t = Tournament.objects.create(
            slug='shared-perm', name='Shared Perm', active=True,
        )
        self.shared_member_t = Tournament.objects.create(
            slug='shared-member', name='Shared Member', active=True,
        )
        self.listed_t = Tournament.objects.create(
            slug='listed', name='Listed', active=True, is_listed=True,
        )
        self.hidden_t = Tournament.objects.create(
            slug='hidden', name='Hidden', active=True,
        )
        self.inactive_t = Tournament.objects.create(
            slug='inactive', name='Inactive', active=False, is_listed=True,
        )

        # Permissions / memberships ---------------------------------------
        UserPermission.objects.create(
            user=self.perm_user,
            tournament=self.shared_perm_t,
            permission='view.team',
        )
        group = Group.objects.create(
            name='Judges', tournament=self.shared_member_t,
        )
        Membership.objects.create(user=self.member_user, group=group)

    def tearDown(self):
        Tournament.objects.all().delete()
        User.objects.all().delete()

    # -- Owner ---------------------------------------------------------------

    def test_owner_sees_own_tournament(self):
        qs = Tournament.objects.visible_to(self.owner)
        self.assertIn(self.owned_t, qs)

    def test_owner_does_not_see_hidden(self):
        qs = Tournament.objects.visible_to(self.owner)
        self.assertNotIn(self.hidden_t, qs)

    def test_owner_sees_listed(self):
        qs = Tournament.objects.visible_to(self.owner)
        self.assertIn(self.listed_t, qs)

    # -- Permission user -----------------------------------------------------

    def test_perm_user_sees_shared(self):
        qs = Tournament.objects.visible_to(self.perm_user)
        self.assertIn(self.shared_perm_t, qs)

    def test_perm_user_does_not_see_hidden(self):
        qs = Tournament.objects.visible_to(self.perm_user)
        self.assertNotIn(self.hidden_t, qs)

    def test_perm_user_does_not_see_other_shared(self):
        qs = Tournament.objects.visible_to(self.perm_user)
        self.assertNotIn(self.shared_member_t, qs)

    # -- Membership user -----------------------------------------------------

    def test_member_sees_shared(self):
        qs = Tournament.objects.visible_to(self.member_user)
        self.assertIn(self.shared_member_t, qs)

    def test_member_does_not_see_hidden(self):
        qs = Tournament.objects.visible_to(self.member_user)
        self.assertNotIn(self.hidden_t, qs)

    # -- Stranger (no relationship) ------------------------------------------

    def test_stranger_sees_only_listed(self):
        qs = Tournament.objects.visible_to(self.stranger)
        self.assertEqual(set(qs), {self.listed_t})

    # -- Superuser -----------------------------------------------------------

    def test_superuser_sees_all_active(self):
        qs = Tournament.objects.visible_to(self.superuser)
        active = Tournament.objects.filter(active=True)
        self.assertEqual(set(qs), set(active))

    def test_superuser_does_not_see_inactive(self):
        qs = Tournament.objects.visible_to(self.superuser)
        self.assertNotIn(self.inactive_t, qs)

    # -- Anonymous (None / unauthenticated) ----------------------------------

    def test_anon_none_sees_only_listed(self):
        qs = Tournament.objects.visible_to(None)
        self.assertEqual(set(qs), {self.listed_t})

    def test_anon_unauthenticated_sees_only_listed(self):
        from django.contrib.auth.models import AnonymousUser
        qs = Tournament.objects.visible_to(AnonymousUser())
        self.assertEqual(set(qs), {self.listed_t})

    # -- Inactive filter -----------------------------------------------------

    def test_inactive_listed_not_visible(self):
        """Even listed tournaments are hidden when inactive."""
        qs = Tournament.objects.visible_to(self.stranger)
        self.assertNotIn(self.inactive_t, qs)

    # -- Distinct results ----------------------------------------------------

    def test_no_duplicates_with_multiple_roles(self):
        """A user with both permission and membership on the same tournament
        should not see duplicates."""
        UserPermission.objects.create(
            user=self.member_user,
            tournament=self.shared_member_t,
            permission='view.team',
        )
        qs = Tournament.objects.visible_to(self.member_user)
        ids = list(qs.values_list('id', flat=True))
        self.assertEqual(len(ids), len(set(ids)))


class MiddlewareVisibilityTestCase(TestCase):
    """Integration tests for the DebateMiddleware visibility gate.

    The middleware should return 404 (not 403) for tournaments the user
    cannot see, preventing existence leaking.
    """

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@test.com', 'pw')
        self.hidden_t = Tournament.objects.create(
            slug='hidden-mid', name='Hidden Mid', active=True,
        )
        self.listed_t = Tournament.objects.create(
            slug='listed-mid', name='Listed Mid', active=True, is_listed=True,
        )

    def tearDown(self):
        Tournament.objects.all().delete()
        User.objects.all().delete()

    def test_hidden_tournament_returns_404_for_stranger(self):
        self.client.login(username='user', password='pw')
        resp = self.client.get(f'/{self.hidden_t.slug}/')
        self.assertEqual(resp.status_code, 404)

    def test_hidden_tournament_returns_404_for_anon(self):
        resp = self.client.get(f'/{self.hidden_t.slug}/')
        self.assertEqual(resp.status_code, 404)

    def test_guessing_slug_returns_404(self):
        """A user guessing a valid slug they have no access to gets 404."""
        self.client.login(username='user', password='pw')
        resp = self.client.get(f'/{self.hidden_t.slug}/admin/')
        self.assertEqual(resp.status_code, 404)

    def test_response_body_does_not_contain_hidden_name(self):
        """404 page must not reveal the tournament name."""
        self.client.login(username='user', password='pw')
        resp = self.client.get(f'/{self.hidden_t.slug}/')
        self.assertNotContains(resp, self.hidden_t.name, status_code=404)

    def test_listed_tournament_returns_200_for_stranger(self):
        self.client.login(username='user', password='pw')
        resp = self.client.get(f'/{self.listed_t.slug}/')
        self.assertIn(resp.status_code, [200, 302])  # 302 for subdomain redirect

    def test_hidden_tournament_returns_404_for_anon(self):
        resp = self.client.get(f'/{self.hidden_t.slug}/')
        self.assertEqual(resp.status_code, 404)
