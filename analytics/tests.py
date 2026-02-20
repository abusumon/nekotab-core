import re
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, RequestFactory, override_settings

from tournaments.models import Tournament, Round

User = get_user_model()


class TournamentViewUrlTests(TestCase):
    """Test that Tournament.view_url returns correct URLs for all slug types."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def tearDown(self):
        cache.clear()

    def _make_tournament(self, slug, **kwargs):
        defaults = {
            'name': f'Test {slug}',
            'slug': slug,
            'owner': self.user,
        }
        defaults.update(kwargs)
        return Tournament.objects.create(**defaults)

    # ── Slug safety checks ───────────────────────────────────────────

    def test_normal_slug_is_subdomain_safe(self):
        t = self._make_tournament('my-tournament-2025')
        self.assertTrue(t.is_subdomain_safe)

    def test_underscore_slug_is_not_subdomain_safe(self):
        t = self._make_tournament('my_tournament')
        self.assertFalse(t.is_subdomain_safe)

    def test_uppercase_slug_is_subdomain_safe(self):
        # DNS is case-insensitive, but our regex checks lowercase
        # is_subdomain_safe lowercases before checking
        t = self._make_tournament('MyTournament')
        self.assertTrue(t.is_subdomain_safe)

    def test_leading_hyphen_slug_is_not_subdomain_safe(self):
        t = self._make_tournament('-my-tournament')
        self.assertFalse(t.is_subdomain_safe)

    def test_trailing_hyphen_slug_is_not_subdomain_safe(self):
        t = self._make_tournament('my-tournament-')
        self.assertFalse(t.is_subdomain_safe)

    def test_empty_slug_is_not_subdomain_safe(self):
        t = Tournament(name='Empty', slug='', owner=self.user)
        self.assertFalse(t.is_subdomain_safe)

    def test_single_char_slug_is_subdomain_safe(self):
        t = self._make_tournament('a')
        self.assertTrue(t.is_subdomain_safe)

    # ── view_url with subdomain disabled ─────────────────────────────

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_view_url_without_subdomain_returns_path(self):
        t = self._make_tournament('test-tournament')
        url = t.view_url
        self.assertEqual(url, f'/{t.slug}/')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_view_url_underscore_slug_without_subdomain(self):
        t = self._make_tournament('test_tournament')
        url = t.view_url
        self.assertEqual(url, f'/{t.slug}/')

    # ── view_url with subdomain enabled ──────────────────────────────

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_view_url_safe_slug_with_subdomain(self):
        t = self._make_tournament('test-tournament')
        url = t.view_url
        self.assertEqual(url, 'https://test-tournament.nekotab.app/')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_view_url_underscore_slug_with_subdomain_falls_back_to_path(self):
        """Underscore slugs can't be used as DNS labels, must fall back to path."""
        t = self._make_tournament('test_tournament')
        url = t.view_url
        # Should NOT return subdomain URL since underscore is DNS-unsafe
        self.assertEqual(url, f'/{t.slug}/')
        self.assertNotIn('nekotab.app', url)


class DebateMiddlewareTests(TestCase):
    """Test that DebateMiddleware handles missing/broken tournaments gracefully."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            owner=self.user,
        )
        Round.objects.create(
            tournament=self.tournament,
            seq=1,
            name='Round 1',
            draw_type=Round.DrawType.RANDOM,
        )

    def tearDown(self):
        cache.clear()

    def _get_middleware(self):
        from utils.middleware import DebateMiddleware
        return DebateMiddleware(lambda req: None)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_existing_tournament_resolves(self):
        mw = self._get_middleware()
        request = self.factory.get('/test-tournament/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'test-tournament'})
        self.assertIsNone(result)
        self.assertEqual(request.tournament.slug, 'test-tournament')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_missing_tournament_returns_friendly_404(self):
        mw = self._get_middleware()
        request = self.factory.get('/nonexistent-tournament/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'nonexistent-tournament'})
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 404)
        # Should contain friendly content, not a raw error
        content = result.content.decode()
        self.assertIn('Tournament Not Found', content)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_case_insensitive_fallback(self):
        """If slug differs only in case, middleware should still find the tournament."""
        mw = self._get_middleware()
        request = self.factory.get('/Test-Tournament/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'Test-Tournament'})
        # Should resolve successfully via case-insensitive fallback
        self.assertIsNone(result)
        self.assertEqual(request.tournament.slug, 'test-tournament')

    @override_settings(
        SUBDOMAIN_TOURNAMENTS_ENABLED=True,
        SUBDOMAIN_BASE_DOMAIN='nekotab.app',
    )
    def test_subdomain_redirect_for_safe_slug(self):
        mw = self._get_middleware()
        request = self.factory.get('/test-tournament/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'test-tournament'})
        self.assertEqual(result.status_code, 301)
        self.assertIn('test-tournament.nekotab.app', result['Location'])

    @override_settings(
        SUBDOMAIN_TOURNAMENTS_ENABLED=True,
        SUBDOMAIN_BASE_DOMAIN='nekotab.app',
    )
    def test_no_subdomain_redirect_for_unsafe_slug(self):
        """Slugs with underscores should NOT be redirected to subdomain."""
        t = Tournament.objects.create(
            name='Unsafe Slug',
            slug='test_underscore',
            owner=self.user,
        )
        mw = self._get_middleware()
        request = self.factory.get('/test_underscore/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'test_underscore'})
        # Should NOT return a redirect (would resolve normally)
        self.assertIsNone(result)
        self.assertEqual(request.tournament.slug, 'test_underscore')


class TournamentsListViewTests(TestCase):
    """Test the analytics tournaments list view."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='adminpass', email='admin@test.com',
        )
        self.regular_user = User.objects.create_user(
            username='regular', password='pass',
        )
        self.t1 = Tournament.objects.create(
            name='Active Tournament', slug='active-tournament', owner=self.superuser, active=True,
        )
        self.t2 = Tournament.objects.create(
            name='Inactive Tournament', slug='inactive-tournament', owner=self.superuser, active=False,
        )
        self.t3 = Tournament.objects.create(
            name='Underscore Slug', slug='broken_slug', owner=self.superuser, active=True,
        )

    def tearDown(self):
        cache.clear()

    def test_superuser_can_access(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/analytics/tournaments/')
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected(self):
        self.client.login(username='regular', password='pass')
        response = self.client.get('/analytics/tournaments/')
        # Should redirect (not authorized)
        self.assertIn(response.status_code, [302, 403])

    def test_anonymous_user_redirected(self):
        response = self.client.get('/analytics/tournaments/')
        self.assertEqual(response.status_code, 302)

    def test_all_tournaments_listed(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/analytics/tournaments/')
        self.assertContains(response, 'Active Tournament')
        self.assertContains(response, 'Inactive Tournament')
        self.assertContains(response, 'Underscore Slug')

    def test_broken_slug_filter(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/analytics/tournaments/?status=broken')
        self.assertEqual(response.status_code, 200)
        tournaments = response.context['tournaments']
        slugs = [t.slug for t in tournaments]
        self.assertIn('broken_slug', slugs)
        self.assertNotIn('active-tournament', slugs)

    def test_broken_slug_count_in_context(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/analytics/tournaments/')
        self.assertEqual(response.context['broken_slug_count'], 1)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_view_url_in_template(self):
        """The View link should use view_url, not hardcoded path."""
        self.client.login(username='admin', password='adminpass')
        response = self.client.get('/analytics/tournaments/')
        content = response.content.decode()
        # Should contain the path-based URL (since subdomain is off)
        self.assertIn('/active-tournament/', content)
        # Should contain `View →` links
        self.assertIn('View →', content)


class DeletedTournamentTests(TestCase):
    """Test that deleted tournaments are handled gracefully everywhere."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin', password='adminpass', email='admin@test.com',
        )

    def tearDown(self):
        cache.clear()

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_accessing_deleted_tournament_returns_friendly_404(self):
        """After deleting a tournament, accessing its URL should show a friendly error."""
        t = Tournament.objects.create(name='Deleted', slug='deleted-tournament', owner=self.user)
        t.delete()
        response = self.client.get('/deleted-tournament/')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Tournament Not Found', response.content)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_cached_tournament_after_deletion(self):
        """Even if cached, a deleted tournament should not cause errors."""
        t = Tournament.objects.create(name='Cached', slug='cached-tournament', owner=self.user)
        # Prime the cache
        cache.set('cached-tournament_object', t, 3600)
        t.delete()
        # The cached object still exists in cache, but the actual tournament is gone
        # Accessing should work with the cached object (or fail gracefully)
        response = self.client.get('/cached-tournament/')
        # Either works (from cache) or shows friendly 404
        self.assertIn(response.status_code, [200, 404])


class TournamentSlugEdgeCaseTests(TestCase):
    """Test edge cases with tournament slugs."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_slug_with_only_numbers(self):
        t = Tournament.objects.create(name='Numeric', slug='12345', owner=self.user)
        self.assertTrue(t.is_subdomain_safe)

    def test_slug_with_mixed_case(self):
        t = Tournament.objects.create(name='Mixed', slug='NDF-Nationals-2025', owner=self.user)
        self.assertTrue(t.is_subdomain_safe)

    def test_slug_with_consecutive_hyphens(self):
        t = Tournament.objects.create(name='Double Hyphen', slug='test--tournament', owner=self.user)
        self.assertTrue(t.is_subdomain_safe)

    def test_slug_with_underscore_and_hyphen(self):
        t = Tournament.objects.create(name='Mixed Sep', slug='test_my-tournament', owner=self.user)
        self.assertFalse(t.is_subdomain_safe)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_view_url_single_underscore(self):
        t = Tournament.objects.create(name='Underscore', slug='a_b', owner=self.user)
        # Should fall back to path-based URL
        self.assertEqual(t.view_url, '/a_b/')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_view_url_leading_hyphen(self):
        t = Tournament.objects.create(name='Lead Hyphen', slug='-abc', owner=self.user)
        # Should fall back to path-based URL (not DNS-safe)
        self.assertEqual(t.view_url, '/-abc/')
