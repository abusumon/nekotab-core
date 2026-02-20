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


class RedirectLoopRegressionTests(TestCase):
    """Regression tests for the redirect loop bug.

    A redirect loop occurred when ``SubdomainTournamentMiddleware`` tried to
    case-correct the hostname.  Because DNS is case-insensitive, browsers
    always lowercase the hostname, so a 301 to a mixed-case hostname
    immediately re-lowercases and produces an infinite loop.

    These tests verify that no middleware path creates a redirect back to
    itself.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='looptest', password='password')
        self.factory = RequestFactory()

    def tearDown(self):
        cache.clear()

    def _get_subdomain_middleware(self):
        from utils.middleware import SubdomainTournamentMiddleware
        return SubdomainTournamentMiddleware(lambda req: None)

    def _get_debate_middleware(self):
        from utils.middleware import DebateMiddleware
        return DebateMiddleware(lambda req: None)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_mixed_case_slug_no_redirect_loop(self):
        """A mixed-case slug must NOT cause a redirect from subdomain middleware."""
        Tournament.objects.create(name='Mixed', slug='NDF-Nationals', owner=self.user)
        mw = self._get_subdomain_middleware()

        # Simulate browser hitting lowercase hostname
        request = self.factory.get('/', HTTP_HOST='ndf-nationals.nekotab.app')
        result = mw(request)

        # Must NOT be a redirect (any redirect risks a loop)
        if result is not None and hasattr(result, 'status_code'):
            self.assertNotIn(result.status_code, [301, 302],
                "SubdomainTournamentMiddleware must not redirect for case "
                "mismatch — this causes an infinite redirect loop.")
        # The subdomain label should be set on the request
        self.assertEqual(getattr(request, 'subdomain_tournament', None), 'ndf-nationals')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_underscore_slug_never_redirected_to_subdomain(self):
        """A tournament with underscores must NEVER be redirected to a subdomain."""
        Tournament.objects.create(name='Underscore', slug='my_tournament', owner=self.user)
        mw = self._get_debate_middleware()

        request = self.factory.get('/my_tournament/')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'my_tournament'})

        # Should NOT redirect
        if result is not None and hasattr(result, 'status_code'):
            self.assertNotEqual(result.status_code, 301,
                "Underscore slug must not be redirected to subdomain (invalid DNS label).")
        self.assertEqual(request.tournament.slug, 'my_tournament')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_subdomain_request_does_not_redirect_again(self):
        """When already on the subdomain, DebateMiddleware must not redirect back."""
        Tournament.objects.create(name='Test', slug='test-tournament', owner=self.user)

        smw = self._get_subdomain_middleware()
        dmw = self._get_debate_middleware()

        request = self.factory.get('/', HTTP_HOST='test-tournament.nekotab.app')
        request.user = self.user

        # First, SubdomainTournamentMiddleware sets the label
        smw(request)
        self.assertEqual(request.subdomain_tournament, 'test-tournament')

        # Then, DebateMiddleware should resolve the tournament, NOT redirect
        result = dmw.process_view(request, None, [],
                                  {'tournament_slug': 'test-tournament'})
        self.assertIsNone(result, "DebateMiddleware must not redirect when already on subdomain.")
        self.assertEqual(request.tournament.slug, 'test-tournament')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=True, SUBDOMAIN_BASE_DOMAIN='nekotab.app')
    def test_base_domain_redirects_only_once(self):
        """A request to the base domain path should redirect exactly once to the subdomain."""
        Tournament.objects.create(name='Test', slug='test-tournament', owner=self.user)
        mw = self._get_debate_middleware()

        request = self.factory.get('/test-tournament/', HTTP_HOST='nekotab.app')
        request.user = self.user
        request.subdomain_tournament = None
        result = mw.process_view(request, None, [], {'tournament_slug': 'test-tournament'})

        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 301)
        location = result['Location']
        self.assertIn('test-tournament.nekotab.app', location)
        # Hostname in redirect MUST be lowercase
        import re
        hostname_match = re.search(r'://([^/]+)', location)
        if hostname_match:
            self.assertEqual(hostname_match.group(1), hostname_match.group(1).lower(),
                "Redirect hostname must be lowercase to prevent loops.")


class DNSSafeSlugValidationTests(TestCase):
    """Test DNS-safe slug enforcement at tournament creation."""

    def test_normalize_slug_basic(self):
        from tournaments.models import normalize_slug
        self.assertEqual(normalize_slug('My Tournament'), 'my-tournament')
        self.assertEqual(normalize_slug('test_slug'), 'test-slug')
        self.assertEqual(normalize_slug('Test_My Tournament'), 'test-my-tournament')
        self.assertEqual(normalize_slug('--leading-trailing--'), 'leading-trailing')
        self.assertEqual(normalize_slug('!!!'), 'tournament')
        self.assertEqual(normalize_slug('UPPER'), 'upper')
        self.assertEqual(normalize_slug('multiple   spaces'), 'multiple-spaces')
        self.assertEqual(normalize_slug('a__b'), 'a-b')

    def test_validate_dns_safe_slug_rejects_underscore(self):
        from django.core.exceptions import ValidationError
        from tournaments.models import validate_dns_safe_slug
        with self.assertRaises(ValidationError) as ctx:
            validate_dns_safe_slug('test_slug')
        self.assertEqual(ctx.exception.code, 'underscore')
        self.assertIn('test-slug', str(ctx.exception.message))

    def test_validate_dns_safe_slug_rejects_uppercase(self):
        from django.core.exceptions import ValidationError
        from tournaments.models import validate_dns_safe_slug
        with self.assertRaises(ValidationError) as ctx:
            validate_dns_safe_slug('MyTournament')
        self.assertEqual(ctx.exception.code, 'uppercase')

    def test_validate_dns_safe_slug_accepts_valid(self):
        from tournaments.models import validate_dns_safe_slug
        # Should not raise
        validate_dns_safe_slug('my-tournament-2025')
        validate_dns_safe_slug('australs2016')
        validate_dns_safe_slug('a')
        validate_dns_safe_slug('123')

    def test_form_auto_normalises_slug(self):
        from tournaments.forms import TournamentStartForm
        data = {
            'name': 'Test Tournament',
            'short_name': 'Test',
            'slug': 'My_Tournament',
            'num_prelim_rounds': 5,
        }
        form = TournamentStartForm(data=data)
        # The form should not be valid because of other model validation,
        # but the slug should have been normalised in clean_slug
        form.is_valid()
        self.assertEqual(form.cleaned_data.get('slug'), 'my-tournament')


# ---------------------------------------------------------------------------
# Database Usage Analytics Tests
# ---------------------------------------------------------------------------

class DbUsageViewTests(TestCase):
    """Tests for the /analytics/db-usage/ page."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            'dbadmin', 'dbadmin@test.com', 'password',
        )
        cls.regular_user = User.objects.create_user(
            'dbregular', 'dbregular@test.com', 'password',
        )
        # Create a tournament with some data to verify row counts
        cls.tournament = Tournament.objects.create(
            name='DB Test Tournament',
            short_name='DBTest',
            slug='db-test',
            seq=1,
            active=True,
            owner=cls.superuser,
        )
        cls.round = Round.objects.create(
            tournament=cls.tournament,
            seq=1,
            name='Round 1',
            abbreviation='R1',
        )

    def setUp(self):
        cache.clear()

    def test_superuser_can_access_db_usage(self):
        """Superuser should get 200 on /analytics/db-usage/."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/')
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected_from_db_usage(self):
        """Non-superuser should be redirected away from db-usage."""
        self.client.force_login(self.regular_user)
        response = self.client.get('/analytics/db-usage/')
        self.assertIn(response.status_code, [302, 403])

    def test_anonymous_redirected_from_db_usage(self):
        """Anonymous user should be redirected to login."""
        response = self.client.get('/analytics/db-usage/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_tournament_appears_in_usage_data(self):
        """At least one tournament should appear in the usage data."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/')
        self.assertEqual(response.status_code, 200)
        usage_data = response.context['usage_data']
        self.assertTrue(len(usage_data) >= 1)
        slugs = [t['slug'] for t in usage_data]
        self.assertIn('db-test', slugs)

    def test_row_counts_match_fixtures(self):
        """Row counts for the test tournament should reflect created fixtures."""
        from participants.models import Team, Speaker
        # Create some teams and speakers
        team1 = Team.objects.create(
            tournament=self.tournament,
            reference='Team Alpha',
        )
        team2 = Team.objects.create(
            tournament=self.tournament,
            reference='Team Beta',
        )
        Speaker.objects.create(team=team1, name='Speaker 1')
        Speaker.objects.create(team=team2, name='Speaker 2')
        Speaker.objects.create(team=team1, name='Speaker 3')

        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/')
        usage_data = response.context['usage_data']
        db_test = next(t for t in usage_data if t['slug'] == 'db-test')

        self.assertEqual(db_test['breakdown']['teams']['rows'], 2)
        self.assertEqual(db_test['breakdown']['speakers']['rows'], 3)
        self.assertEqual(db_test['breakdown']['rounds']['rows'], 1)

    def test_search_filter(self):
        """Search filter should filter tournaments by slug/name."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/?search=db-test')
        usage_data = response.context['usage_data']
        self.assertTrue(all('db-test' in t['slug'] or 'db-test' in t['name'].lower()
                            for t in usage_data))

    def test_status_filter_active(self):
        """Status=active should only return active tournaments."""
        Tournament.objects.create(
            name='Inactive Test', slug='inactive-db', seq=2,
            active=False, owner=self.superuser,
        )
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/?status=active')
        usage_data = response.context['usage_data']
        self.assertTrue(all(t['active'] for t in usage_data))

    def test_top_filter(self):
        """Top N filter should limit results."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/?top=1')
        usage_data = response.context['usage_data']
        self.assertTrue(len(usage_data) <= 1)

    def test_refresh_cache_requires_post(self):
        """GET to refresh endpoint should not work (method not allowed)."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/refresh/')
        self.assertEqual(response.status_code, 405)

    def test_refresh_cache_clears_and_redirects(self):
        """POST to refresh should clear cache and redirect to db-usage."""
        self.client.force_login(self.superuser)
        # Prime the cache
        self.client.get('/analytics/db-usage/')
        self.assertIsNotNone(cache.get('analytics_db_usage_v1'))
        # Refresh
        response = self.client.post('/analytics/db-usage/refresh/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('db-usage', response.url)
        self.assertIsNone(cache.get('analytics_db_usage_v1'))

    def test_totals_in_context(self):
        """Context should contain totals dict."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/db-usage/')
        totals = response.context['totals']
        self.assertIn('rows', totals)
        self.assertIn('tournament_count', totals)
        self.assertGreaterEqual(totals['tournament_count'], 1)

    def test_refresh_requires_superuser(self):
        """Non-superuser should be blocked from refresh endpoint."""
        self.client.force_login(self.regular_user)
        response = self.client.post('/analytics/db-usage/refresh/')
        self.assertIn(response.status_code, [302, 403])


# ---------------------------------------------------------------------------
# Tournament Deletion Tests
# ---------------------------------------------------------------------------

class DeleteTournamentsViewTests(TestCase):
    """Tests for POST /analytics/tournaments/delete/."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            'deladmin', 'deladmin@test.com', 'password',
        )
        cls.regular_user = User.objects.create_user(
            'delregular', 'delregular@test.com', 'password',
        )

    def setUp(self):
        cache.clear()
        self.tournament = Tournament.objects.create(
            name='Delete Me', short_name='DelMe', slug='delete-me',
            seq=1, active=True, owner=self.superuser,
        )
        self.round = Round.objects.create(
            tournament=self.tournament, seq=1,
            name='Round 1', abbreviation='R1',
        )

    def tearDown(self):
        cache.clear()

    def _post_delete(self, ids, user=None):
        import json
        self.client.force_login(user or self.superuser)
        return self.client.post(
            '/analytics/tournaments/delete/',
            data=json.dumps({'tournament_ids': ids}),
            content_type='application/json',
        )

    # --- Access control ---

    def test_requires_superuser(self):
        """Non-superuser should be blocked."""
        response = self._post_delete([self.tournament.id], user=self.regular_user)
        self.assertIn(response.status_code, [302, 403])

    def test_anonymous_blocked(self):
        """Anonymous user should be redirected to login."""
        import json
        response = self.client.post(
            '/analytics/tournaments/delete/',
            data=json.dumps({'tournament_ids': [self.tournament.id]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_get_not_allowed(self):
        """GET method should return 405."""
        self.client.force_login(self.superuser)
        response = self.client.get('/analytics/tournaments/delete/')
        self.assertEqual(response.status_code, 405)

    # --- Validation ---

    def test_empty_body_returns_400(self):
        """Invalid JSON body should return 400."""
        self.client.force_login(self.superuser)
        response = self.client.post(
            '/analytics/tournaments/delete/',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_ids_returns_400(self):
        """Empty tournament_ids list should return 400."""
        response = self._post_delete([])
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_ids_returns_404(self):
        """IDs that don't match any tournament should return 404."""
        response = self._post_delete([99999])
        self.assertEqual(response.status_code, 404)

    def test_non_integer_ids_returns_400(self):
        """Non-integer IDs should return 400."""
        import json
        self.client.force_login(self.superuser)
        response = self.client.post(
            '/analytics/tournaments/delete/',
            data=json.dumps({'tournament_ids': ['abc']}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    # --- Single deletion ---

    def test_single_delete_success(self):
        """Superuser can delete a single tournament."""
        tid = self.tournament.id
        response = self._post_delete([tid])
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['deleted_count'], 1)
        self.assertEqual(data['failed_count'], 0)
        self.assertEqual(data['deleted'][0]['id'], tid)
        self.assertFalse(Tournament.objects.filter(id=tid).exists())

    def test_cascade_deletes_rounds(self):
        """Deleting a tournament should cascade-delete its rounds."""
        round_id = self.round.id
        self._post_delete([self.tournament.id])
        self.assertFalse(Round.objects.filter(id=round_id).exists())

    def test_audit_log_created(self):
        """Deletion should create a TournamentDeletionLog entry."""
        from retention.models import TournamentDeletionLog
        tid = self.tournament.id
        self._post_delete([tid])
        log = TournamentDeletionLog.objects.filter(
            tournament_id=tid,
            status=TournamentDeletionLog.Status.DELETED,
        )
        self.assertTrue(log.exists())
        entry = log.first()
        self.assertEqual(entry.slug, 'delete-me')
        self.assertEqual(entry.name, 'Delete Me')

    # --- Bulk deletion ---

    def test_bulk_delete(self):
        """Multiple tournaments should be deleted in one request."""
        t2 = Tournament.objects.create(
            name='Delete Me Too', short_name='DM2', slug='delete-me-2',
            seq=2, active=True, owner=self.superuser,
        )
        Round.objects.create(
            tournament=t2, seq=1, name='R1', abbreviation='R1',
        )
        ids = [self.tournament.id, t2.id]
        response = self._post_delete(ids)
        data = response.json()
        self.assertEqual(data['deleted_count'], 2)
        self.assertFalse(Tournament.objects.filter(id__in=ids).exists())

    def test_partial_failure_reports_both(self):
        """If some IDs are valid and some are not, only existing ones are deleted."""
        tid = self.tournament.id
        response = self._post_delete([tid, 99999])
        data = response.json()
        # 99999 doesn't exist so queryset only picks up the valid one
        self.assertEqual(data['deleted_count'], 1)
        self.assertFalse(Tournament.objects.filter(id=tid).exists())

    # --- Cache busting ---

    def test_db_usage_cache_cleared(self):
        """Deletion should bust the DB usage cache."""
        cache.set('analytics_db_usage_v1', {'dummy': True}, 3600)
        self._post_delete([self.tournament.id])
        self.assertIsNone(cache.get('analytics_db_usage_v1'))

    # --- Related data (team + debate) ---

    def test_cascade_deletes_teams_and_debates(self):
        """Teams, debates, and related objects should cascade-delete."""
        from participants.models import Team
        from draw.models import Debate

        team = Team.objects.create(
            tournament=self.tournament, reference='Team X',
        )
        debate = Debate.objects.create(round=self.round)

        self._post_delete([self.tournament.id])
        self.assertFalse(Team.objects.filter(id=team.id).exists())
        self.assertFalse(Debate.objects.filter(id=debate.id).exists())
