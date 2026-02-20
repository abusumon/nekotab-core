"""Tests for SubdomainTournamentMiddleware and subdomain-aware URL generation."""

from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model

from tournaments.models import Tournament
from utils.middleware import SubdomainTournamentMiddleware, get_subdomain_url
from utils.misc import build_tournament_absolute_uri

User = get_user_model()

SUBDOMAIN_SETTINGS = {
    'SUBDOMAIN_TOURNAMENTS_ENABLED': True,
    'SUBDOMAIN_BASE_DOMAIN': 'nekotab.app',
    'RESERVED_SUBDOMAINS': ['www', 'admin', 'api', 'static', 'media', 'jet', 'database'],
    'ALLOWED_HOSTS': ['*'],
}


@override_settings(**SUBDOMAIN_SETTINGS)
class SubdomainMiddlewareTest(TestCase):
    """Test that SubdomainTournamentMiddleware correctly rewrites paths."""

    @classmethod
    def setUpTestData(cls):
        cls.tournament = Tournament.objects.create(
            name='Test Tournament',
            short_name='Test',
            slug='test-tourney',
            seq=1,
            active=True,
        )
        cls.tournament2 = Tournament.objects.create(
            name='Other Tournament',
            short_name='Other',
            slug='other-tourney',
            seq=2,
            active=True,
        )

    def test_subdomain_root_maps_to_tournament(self):
        """GET https://test-tourney.nekotab.app/ should resolve the tournament."""
        response = self.client.get('/', HTTP_HOST='test-tourney.nekotab.app')
        self.assertEqual(response.status_code, 200)

    def test_subdomain_subpage_works(self):
        """GET https://test-tourney.nekotab.app/motions/ should work."""
        # The 302/200 depends on whether the tournament has rounds;
        # we mainly verify it doesn't 404 or 500.
        response = self.client.get('/motions/', HTTP_HOST='test-tourney.nekotab.app')
        self.assertIn(response.status_code, [200, 302])

    def test_path_based_access_still_works(self):
        """GET https://nekotab.app/test-tourney/ should still work."""
        response = self.client.get('/test-tourney/', HTTP_HOST='nekotab.app')
        self.assertEqual(response.status_code, 200)

    def test_path_based_subpage_still_works(self):
        """GET https://nekotab.app/test-tourney/motions/ should still work."""
        response = self.client.get('/test-tourney/motions/', HTTP_HOST='nekotab.app')
        self.assertIn(response.status_code, [200, 302])

    def test_reserved_subdomain_not_tournament(self):
        """GET https://admin.nekotab.app/ should NOT route as a tournament."""
        response = self.client.get('/', HTTP_HOST='admin.nekotab.app')
        # Should hit the site home page, not a tournament
        self.assertEqual(response.status_code, 200)

    def test_www_subdomain_ignored(self):
        """GET https://www.nekotab.app/ should not route as tournament."""
        response = self.client.get('/', HTTP_HOST='www.nekotab.app')
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_subdomain_ignored(self):
        """GET https://nonexistent.nekotab.app/ should not 500."""
        response = self.client.get('/', HTTP_HOST='nonexistent.nekotab.app')
        # Returns site home since 'nonexistent' isn't a real tournament
        self.assertEqual(response.status_code, 200)

    def test_global_paths_not_rewritten(self):
        """Analytics/static/database paths should not be rewritten on subdomains."""
        for path in ['/analytics/', '/static/css/style.css', '/database/']:
            response = self.client.get(path, HTTP_HOST='test-tourney.nekotab.app')
            # Should not produce a 500 from double-prefixing
            self.assertNotEqual(response.status_code, 500,
                                msg=f"Path {path} returned 500 on tournament subdomain")

    def test_tournament_admin_paths_rewritten_on_subdomain(self):
        """Tournament admin paths like /admin/configure/ MUST be rewritten on subdomains.

        These are tournament-scoped pages, not Django admin. The Django admin
        lives at /database/ and is excluded via BAD_PREFIXES. Tournament admin
        paths must be rewritten so that Django's URL resolver can match them
        against <slug:tournament_slug>/admin/... patterns.
        """
        factory = RequestFactory()
        request = factory.get('/admin/configure/', HTTP_HOST='test-tourney.nekotab.app')

        def get_response(req):
            # Path should be rewritten with slug prefix
            self.assertEqual(req.path_info, '/test-tourney/admin/configure/')
            self.assertEqual(req.subdomain_tournament, 'test-tourney')
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = SubdomainTournamentMiddleware(get_response)
        middleware(request)

    def test_no_double_prefix_for_other_tournament(self):
        """If path already has another tournament's slug, don't double-prefix."""
        # Visiting /other-tourney/ on test-tourney.nekotab.app
        response = self.client.get('/other-tourney/',
                                   HTTP_HOST='test-tourney.nekotab.app')
        # Should render other-tourney's page, not 404/500
        self.assertIn(response.status_code, [200, 302])

    def test_subdomain_flag_set_on_request(self):
        """The middleware should set request.subdomain_tournament."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='test-tourney.nekotab.app')

        def get_response(req):
            # Verify the flag was set before the response
            self.assertEqual(req.subdomain_tournament, 'test-tourney')
            self.assertEqual(req.path_info, '/test-tourney/')
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = SubdomainTournamentMiddleware(get_response)
        middleware(request)

    def test_subdomain_flag_none_for_root_domain(self):
        """Root domain requests should have subdomain_tournament = None."""
        factory = RequestFactory()
        request = factory.get('/test-tourney/', HTTP_HOST='nekotab.app')

        def get_response(req):
            self.assertIsNone(req.subdomain_tournament)
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = SubdomainTournamentMiddleware(get_response)
        middleware(request)

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_disabled_subdomain_routing(self):
        """When disabled, subdomains should not be rewritten."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='test-tourney.nekotab.app')

        def get_response(req):
            self.assertIsNone(req.subdomain_tournament)
            self.assertEqual(req.path_info, '/')
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = SubdomainTournamentMiddleware(get_response)
        middleware(request)


@override_settings(**SUBDOMAIN_SETTINGS)
class GetSubdomainUrlTest(TestCase):
    """Test the get_subdomain_url helper function."""

    def test_basic_url(self):
        url = get_subdomain_url('my-tournament', '/')
        self.assertEqual(url, 'https://my-tournament.nekotab.app/')

    def test_with_path(self):
        url = get_subdomain_url('my-tournament', '/motions/')
        self.assertEqual(url, 'https://my-tournament.nekotab.app/motions/')

    def test_path_without_leading_slash(self):
        url = get_subdomain_url('my-tournament', 'results/')
        self.assertEqual(url, 'https://my-tournament.nekotab.app/results/')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_returns_none_when_disabled(self):
        url = get_subdomain_url('my-tournament', '/')
        self.assertIsNone(url)

    @override_settings(SUBDOMAIN_BASE_DOMAIN='')
    def test_returns_none_without_base_domain(self):
        url = get_subdomain_url('my-tournament', '/')
        self.assertIsNone(url)


@override_settings(**SUBDOMAIN_SETTINGS)
class CanonicalUrlTest(TestCase):
    """Test that canonical URLs use subdomain form on subdomain requests."""

    @classmethod
    def setUpTestData(cls):
        cls.tournament = Tournament.objects.create(
            name='Canonical Test',
            short_name='Canonical',
            slug='canonical-test',
            seq=1,
            active=True,
        )

    def test_canonical_url_on_subdomain(self):
        """Canonical URL should use subdomain form when on subdomain."""
        response = self.client.get('/', HTTP_HOST='canonical-test.nekotab.app')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('https://canonical-test.nekotab.app/', content)

    def test_canonical_url_on_path(self):
        """Canonical URL should use path form when on root domain."""
        response = self.client.get('/canonical-test/', HTTP_HOST='nekotab.app')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('https://nekotab.app/canonical-test/', content)


@override_settings(**SUBDOMAIN_SETTINGS)
class BuildTournamentAbsoluteUriTest(TestCase):
    """Test the build_tournament_absolute_uri helper avoids double-slug."""

    @classmethod
    def setUpTestData(cls):
        cls.tournament = Tournament.objects.create(
            name='URI Test',
            short_name='URI',
            slug='uri-test',
            seq=1,
            active=True,
        )

    def test_subdomain_strips_slug_prefix(self):
        """Path /uri-test/motions/ should become https://uri-test.nekotab.app/motions/."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='uri-test.nekotab.app', secure=True)
        url = build_tournament_absolute_uri(request, self.tournament, '/uri-test/motions/')
        self.assertEqual(url, 'https://uri-test.nekotab.app/motions/')

    def test_subdomain_root_path(self):
        """None path should become https://uri-test.nekotab.app/uri-test/"""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='uri-test.nekotab.app', secure=True)
        url = build_tournament_absolute_uri(request, self.tournament)
        self.assertEqual(url, 'https://uri-test.nekotab.app/')

    def test_subdomain_path_without_slug_prefix(self):
        """Path /motions/ stays as /motions/ on subdomain."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='uri-test.nekotab.app', secure=True)
        url = build_tournament_absolute_uri(request, self.tournament, '/motions/')
        self.assertEqual(url, 'https://uri-test.nekotab.app/motions/')

    @override_settings(SUBDOMAIN_TOURNAMENTS_ENABLED=False)
    def test_fallback_to_build_absolute_uri(self):
        """When subdomain disabled, falls back to request.build_absolute_uri."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='nekotab.app')
        url = build_tournament_absolute_uri(request, self.tournament, '/uri-test/motions/')
        self.assertIn('/uri-test/motions/', url)

    def test_no_double_slug_with_reverse_tournament(self):
        """Simulating a typical view call: reverse_tournament + build_tournament_absolute_uri."""
        from utils.misc import reverse_tournament
        factory = RequestFactory()
        request = factory.get('/', HTTP_HOST='uri-test.nekotab.app', secure=True)
        path = reverse_tournament('tournament-admin-home', self.tournament)
        url = build_tournament_absolute_uri(request, self.tournament, path)
        # Should NOT contain /uri-test/uri-test/
        self.assertNotIn('/uri-test/uri-test/', url)
        # Should contain the slug exactly once in the domain
        self.assertTrue(url.startswith('https://uri-test.nekotab.app/'))


@override_settings(**SUBDOMAIN_SETTINGS)
class TournamentCreationFlowTest(TestCase):
    """Regression tests for the tournament creation → configure flow.

    These verify the fix for the bug where /admin/configure/ on a tournament
    subdomain returned 404 because SubdomainTournamentMiddleware skipped URL
    rewriting for paths starting with /admin/.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            'superadmin', 'admin@test.com', 'password',
        )

    def test_superuser_can_open_create_tournament_page(self):
        """Superuser can access /create/ on the base domain."""
        self.client.force_login(self.superuser)
        response = self.client.get('/create/', HTTP_HOST='nekotab.app')
        self.assertEqual(response.status_code, 200)

    def test_redirect_tournament_generates_correct_url(self):
        """redirect_tournament('tournament-configure', t) should produce a
        valid subdomain URL pointing to /admin/configure/."""
        from utils.misc import _to_subdomain_url
        from django.urls import reverse
        t = Tournament.objects.create(
            slug='test-create', name='Test Create', seq=1, active=True,
            owner=self.superuser,
        )
        path = reverse('tournament-configure',
                        kwargs={'tournament_slug': t.slug})
        self.assertEqual(path, '/test-create/admin/configure/')
        subdomain_url = _to_subdomain_url(t.slug, path)
        self.assertEqual(subdomain_url,
                         'https://test-create.nekotab.app/admin/configure/')

    def test_configure_route_works_on_subdomain(self):
        """GET /admin/configure/ on the tournament subdomain should NOT 404."""
        t = Tournament.objects.create(
            slug='cfg-sub', name='Configure Sub', seq=1, active=True,
            owner=self.superuser,
        )
        self.client.force_login(self.superuser)
        response = self.client.get('/admin/configure/',
                                   HTTP_HOST='cfg-sub.nekotab.app')
        # Should resolve (200) or redirect (302), never 404
        self.assertIn(response.status_code, [200, 302],
                      msg=f"Expected 200/302, got {response.status_code}")

    def test_configure_route_works_on_base_domain_path(self):
        """GET /cfg-path/admin/configure/ on the base domain should work."""
        t = Tournament.objects.create(
            slug='cfg-path', name='Configure Path', seq=1, active=True,
            owner=self.superuser,
        )
        self.client.force_login(self.superuser)
        response = self.client.get('/cfg-path/admin/configure/',
                                   HTTP_HOST='nekotab.app')
        self.assertIn(response.status_code, [200, 301, 302])

    def test_tournament_admin_home_works_on_subdomain(self):
        """GET /admin/ on the tournament subdomain should resolve."""
        t = Tournament.objects.create(
            slug='admin-sub', name='Admin Sub', seq=1, active=True,
            owner=self.superuser,
        )
        self.client.force_login(self.superuser)
        response = self.client.get('/admin/',
                                   HTTP_HOST='admin-sub.nekotab.app')
        self.assertIn(response.status_code, [200, 302])

    def test_visibility_gate_does_not_block_superuser(self):
        """Superuser should never be blocked by the visibility gate."""
        t = Tournament.objects.create(
            slug='hidden-su', name='Hidden SU', seq=1, active=True,
            is_listed=False,
        )
        self.client.force_login(self.superuser)
        response = self.client.get('/',
                                   HTTP_HOST='hidden-su.nekotab.app')
        self.assertNotEqual(response.status_code, 404,
                            msg="Superuser should not get 404 for unlisted tournament")

    def test_visibility_gate_blocks_anonymous(self):
        """Anonymous users should get 404 for unlisted tournaments."""
        t = Tournament.objects.create(
            slug='hidden-anon', name='Hidden Anon', seq=1, active=True,
            is_listed=False,
        )
        response = self.client.get('/',
                                   HTTP_HOST='hidden-anon.nekotab.app')
        self.assertEqual(response.status_code, 404)

    def test_no_redirect_loop_in_create_flow(self):
        """Creating a tournament and following the redirect should not loop."""
        self.client.force_login(self.superuser)
        # POST to create
        response = self.client.post('/create/', {
            'name': 'Loop Test',
            'short_name': 'Loop',
            'slug': 'loop-test',
            'seq': 1,
        }, HTTP_HOST='nekotab.app')
        # Should redirect (302)
        self.assertEqual(response.status_code, 302)
        redirect_url = response['Location']
        # The redirect should point to the configure page on subdomain
        self.assertIn('loop-test', redirect_url)
        self.assertIn('/admin/configure/', redirect_url)

    def test_subdomain_cache_warmed_after_creation(self):
        """After tournament creation, the subdomain cache should be warm."""
        from django.core.cache import cache
        self.client.force_login(self.superuser)
        self.client.post('/create/', {
            'name': 'Cache Warm Test',
            'short_name': 'CW',
            'slug': 'cache-warm',
            'seq': 1,
        }, HTTP_HOST='nekotab.app')
        cached = cache.get('subdom_tour_exists_cache-warm')
        self.assertTrue(cached,
                        msg="Subdomain cache should be True after creation")
