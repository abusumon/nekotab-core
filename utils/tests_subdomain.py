"""Tests for SubdomainTournamentMiddleware and subdomain-aware URL generation."""

from unittest.mock import patch

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model

from tournaments.models import Tournament
from utils.middleware import SubdomainTournamentMiddleware, get_subdomain_url

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
        """Admin/analytics/static paths should not be rewritten on subdomains."""
        for path in ['/admin/', '/analytics/', '/static/css/style.css']:
            response = self.client.get(path, HTTP_HOST='test-tourney.nekotab.app')
            # Should not produce a 500 from double-prefixing
            self.assertNotEqual(response.status_code, 500,
                                msg=f"Path {path} returned 500 on tournament subdomain")

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
