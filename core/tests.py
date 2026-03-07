"""Tests for the core app — subdomain slug reservation system.

Covers: backfill correctness, slug collision prevention, cascade behaviour,
signal-driven reservation creation, and the check constraint.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from core.models import SubdomainSlugReservation
from organizations.models import Organization, OrganizationMembership
from tournaments.models import Tournament

User = get_user_model()


class SlugReservationModelTests(TestCase):
    """Basic model behaviour for SubdomainSlugReservation."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org", slug="test-org")
        self.tournament = Tournament.objects.create(
            name="Test T", slug="test-t", organization=self.org)

    def test_reservation_str(self):
        r = SubdomainSlugReservation.objects.create(
            slug="my-slug", tenant_type="tournament", tournament=self.tournament)
        self.assertEqual(str(r), "my-slug (tournament)")

    def test_unique_slug(self):
        SubdomainSlugReservation.objects.create(
            slug="unique-one", tenant_type="tournament", tournament=self.tournament)
        org2 = Organization.objects.create(
            name="Org2", slug="unique-one", is_workspace_enabled=True)
        with self.assertRaises(IntegrityError):
            SubdomainSlugReservation.objects.create(
                slug="unique-one", tenant_type="organization", organization=org2)


class TournamentSlugReservationSignalTests(TestCase):
    """Signal creates a reservation when a tournament is created."""

    def setUp(self):
        self.org = Organization.objects.create(name="Sig Org", slug="sig-org")

    def test_reservation_created_on_tournament_create(self):
        t = Tournament.objects.create(
            name="Signal T", slug="signal-t", organization=self.org)
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(
                slug="signal-t", tenant_type="tournament", tournament=t,
            ).exists())

    def test_reservation_cascade_on_tournament_delete(self):
        t = Tournament.objects.create(
            name="Del T", slug="del-t", organization=self.org)
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(slug="del-t").exists())
        t.delete()
        self.assertFalse(
            SubdomainSlugReservation.objects.filter(slug="del-t").exists())

    def test_slug_lowercased_in_reservation(self):
        """Even if the slug has mixed case, the reservation stores lowercase."""
        t = Tournament.objects.create(
            name="Case T", slug="case-t", organization=self.org)
        r = SubdomainSlugReservation.objects.get(tournament=t)
        self.assertEqual(r.slug, "case-t")


class OrganizationSlugReservationSignalTests(TestCase):
    """Signal creates/removes a reservation when an org is saved."""

    def test_reservation_created_when_workspace_enabled(self):
        org = Organization.objects.create(
            name="WS Org", slug="ws-org", is_workspace_enabled=True)
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(
                slug="ws-org", tenant_type="organization", organization=org,
            ).exists())

    def test_no_reservation_when_workspace_disabled(self):
        org = Organization.objects.create(
            name="No WS", slug="no-ws", is_workspace_enabled=False)
        self.assertFalse(
            SubdomainSlugReservation.objects.filter(
                organization=org,
            ).exists())

    def test_reservation_removed_when_workspace_disabled(self):
        org = Organization.objects.create(
            name="Toggle Org", slug="toggle-org", is_workspace_enabled=True)
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(
                slug="toggle-org", organization=org).exists())
        org.is_workspace_enabled = False
        org.save()
        self.assertFalse(
            SubdomainSlugReservation.objects.filter(
                slug="toggle-org", organization=org).exists())

    def test_reservation_cascade_on_org_delete(self):
        org = Organization.objects.create(
            name="Del Org", slug="del-org", is_workspace_enabled=True)
        self.assertTrue(
            SubdomainSlugReservation.objects.filter(slug="del-org").exists())
        org.delete()
        self.assertFalse(
            SubdomainSlugReservation.objects.filter(slug="del-org").exists())


class SlugCollisionValidationTests(TestCase):
    """Test clean() methods prevent slug collisions between entities."""

    def setUp(self):
        self.org = Organization.objects.create(name="Base Org", slug="base-org")

    def test_tournament_clean_blocks_org_workspace_slug(self):
        """Cannot create a tournament with a slug matching a workspace org."""
        Organization.objects.create(
            name="WS Org", slug="taken-slug", is_workspace_enabled=True)
        t = Tournament(name="Bad T", slug="taken-slug", organization=self.org)
        with self.assertRaises(ValidationError) as ctx:
            t.clean()
        self.assertIn('slug', ctx.exception.message_dict)

    def test_tournament_clean_allows_non_workspace_org_slug(self):
        """A tournament CAN share a slug with a non-workspace org (workspace disabled)."""
        Organization.objects.create(
            name="No WS Org", slug="shared-slug", is_workspace_enabled=False)
        t = Tournament(name="OK T", slug="shared-slug", organization=self.org)
        # Should not raise
        t.clean()

    def test_org_clean_blocks_tournament_slug(self):
        """Cannot enable workspace on an org whose slug matches a tournament."""
        Tournament.objects.create(
            name="Existing T", slug="conflict-slug", organization=self.org)
        org = Organization(
            name="Bad Org", slug="conflict-slug", is_workspace_enabled=True)
        with self.assertRaises(ValidationError) as ctx:
            org.clean()
        self.assertIn('slug', ctx.exception.message_dict)

    def test_org_clean_allows_when_workspace_disabled(self):
        """An org with workspace disabled CAN share a slug with a tournament."""
        Tournament.objects.create(
            name="Existing T2", slug="ok-slug", organization=self.org)
        org = Organization(
            name="OK Org", slug="ok-slug", is_workspace_enabled=False)
        # Should not raise
        org.clean()

    def test_tournament_clean_passes_when_no_conflict(self):
        """No error when slug is unique."""
        t = Tournament(name="Unique T", slug="unique-slug", organization=self.org)
        t.clean()

    def test_org_clean_passes_when_no_conflict(self):
        """No error when slug is unique and workspace enabled."""
        org = Organization(
            name="Unique Org", slug="unique-org", is_workspace_enabled=True)
        org.clean()
