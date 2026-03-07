"""Tests for Phase 7: Registration flows — tournament and organization creation
from the bare domain."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import SubdomainSlugReservation
from organizations.models import Organization, OrganizationMembership
from tournaments.models import Tournament, Round

User = get_user_model()

REGISTRATION_SETTINGS = {
    'SUBDOMAIN_TOURNAMENTS_ENABLED': True,
    'SUBDOMAIN_BASE_DOMAIN': 'nekotab.app',
    'ORGANIZATION_WORKSPACES_ENABLED': True,
    'RESERVED_SUBDOMAINS': ['www', 'admin', 'api', 'static', 'media'],
    'ALLOWED_HOSTS': ['*'],
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


@override_settings(**REGISTRATION_SETTINGS)
class RegisterTournamentTest(TestCase):
    """Test /register/tournament/ flow."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='password')

    def test_register_tournament_creates_phantom_org(self):
        """Creating a tournament auto-creates a non-workspace org."""
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/tournament/', {
            'name': 'My Open',
            'short_name': 'MO',
            'slug': 'my-open',
            'num_prelim_rounds': 5,
        })
        self.assertEqual(response.status_code, 302)
        t = Tournament.objects.get(slug='my-open')
        self.assertFalse(t.organization.is_workspace_enabled)
        self.assertEqual(t.owner, self.user)
        self.assertEqual(Round.objects.filter(tournament=t).count(), 5)

    def test_register_tournament_creates_membership(self):
        """Creator becomes OWNER of the auto-created org."""
        self.client.login(username='testuser', password='password')
        self.client.post('/register/tournament/', {
            'name': 'My Open',
            'short_name': 'MO',
            'slug': 'my-open-2',
            'num_prelim_rounds': 3,
        })
        t = Tournament.objects.get(slug='my-open-2')
        self.assertTrue(OrganizationMembership.objects.filter(
            organization=t.organization,
            user=self.user,
            role=OrganizationMembership.Role.OWNER,
        ).exists())

    def test_register_tournament_creates_slug_reservation(self):
        """Tournament slug is reserved in SubdomainSlugReservation."""
        self.client.login(username='testuser', password='password')
        self.client.post('/register/tournament/', {
            'name': 'Reserved Tourney',
            'short_name': 'RT',
            'slug': 'reserved-tourney',
            'num_prelim_rounds': 3,
        })
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(slug='reserved-tourney').exists())

    def test_unauthenticated_redirects(self):
        """Anonymous users are redirected to login."""
        response = self.client.get('/register/tournament/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_get_renders_form(self):
        """GET shows the registration form."""
        self.client.login(username='testuser', password='password')
        response = self.client.get('/register/tournament/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="slug"')


@override_settings(**REGISTRATION_SETTINGS)
class RegisterOrganizationTest(TestCase):
    """Test /register/organization/ flow."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='password')

    def test_register_organization_creates_workspace(self):
        """Creating an org enables workspace and creates OWNER membership."""
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/organization/', {
            'name': 'My Debate Society',
            'slug': 'my-debate',
            'description': '',
        })
        self.assertEqual(response.status_code, 302)
        org = Organization.objects.get(slug='my-debate')
        self.assertTrue(org.is_workspace_enabled)
        self.assertTrue(OrganizationMembership.objects.filter(
            organization=org,
            user=self.user,
            role=OrganizationMembership.Role.OWNER,
        ).exists())

    def test_register_organization_creates_slug_reservation(self):
        """Org slug is reserved in SubdomainSlugReservation."""
        self.client.login(username='testuser', password='password')
        self.client.post('/register/organization/', {
            'name': 'Reserved Org',
            'slug': 'reserved-org',
            'description': '',
        })
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(slug='reserved-org').exists())

    def test_register_organization_redirects_to_workspace(self):
        """After creation, redirects to the workspace subdomain."""
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/organization/', {
            'name': 'Redirect Org',
            'slug': 'redirect-org',
            'description': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('redirect-org.nekotab.app', response.url)

    def test_unauthenticated_redirects(self):
        """Anonymous users are redirected to login."""
        response = self.client.get('/register/organization/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_get_renders_form(self):
        """GET shows the registration form."""
        self.client.login(username='testuser', password='password')
        response = self.client.get('/register/organization/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="slug"')


@override_settings(**REGISTRATION_SETTINGS)
class SlugCollisionTest(TestCase):
    """Cross-entity slug collision tests."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', password='password')
        self.org = Organization.objects.create(
            name='Existing Org', slug='existing-org')
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user,
            role=OrganizationMembership.Role.OWNER)

    def test_slug_collision_tournament_org(self):
        """Org registration rejects slug already used by a tournament."""
        Tournament.objects.create(
            name='Collider', slug='collider', organization=self.org)
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/organization/', {
            'name': 'Collider Org',
            'slug': 'collider',
            'description': '',
        })
        self.assertEqual(response.status_code, 200)  # re-renders form
        self.assertFalse(Organization.objects.filter(slug='collider').exists())

    def test_slug_collision_org_exists(self):
        """Org registration rejects slug already used by another org."""
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/organization/', {
            'name': 'Duplicate Org',
            'slug': 'existing-org',
            'description': '',
        })
        self.assertEqual(response.status_code, 200)  # re-renders form

    def test_slug_collision_reserved(self):
        """Org registration rejects reserved subdomain slugs."""
        self.client.login(username='testuser', password='password')
        response = self.client.post('/register/organization/', {
            'name': 'Admin Org',
            'slug': 'admin',
            'description': '',
        })
        self.assertEqual(response.status_code, 200)  # re-renders form
        self.assertFalse(Organization.objects.filter(slug='admin').exists())
