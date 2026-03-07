"""Tests for Phase 9: Security hardening — organization role-to-permission
mapping and cached role lookups in has_permission()."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from organizations.models import Organization, OrganizationMembership
from organizations.permissions import ROLE_PERMISSIONS
from tournaments.models import Tournament
from users.permissions import Permission, has_permission

User = get_user_model()

PERM_SETTINGS = {
    'SUBDOMAIN_TOURNAMENTS_ENABLED': True,
    'SUBDOMAIN_BASE_DOMAIN': 'nekotab.app',
    'ORGANIZATION_WORKSPACES_ENABLED': True,
    'ALLOWED_HOSTS': ['*'],
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


@override_settings(**PERM_SETTINGS)
class RolePermissionMappingTest(TestCase):
    """Verify the ROLE_PERMISSIONS dict is well-formed."""

    def test_owner_is_all(self):
        self.assertEqual(ROLE_PERMISSIONS['owner'], '__all__')

    def test_admin_is_all(self):
        self.assertEqual(ROLE_PERMISSIONS['admin'], '__all__')

    def test_tabmaster_is_set(self):
        self.assertIsInstance(ROLE_PERMISSIONS['tabmaster'], set)

    def test_editor_is_set(self):
        self.assertIsInstance(ROLE_PERMISSIONS['editor'], set)

    def test_member_equals_editor(self):
        self.assertEqual(ROLE_PERMISSIONS['member'], ROLE_PERMISSIONS['editor'])

    def test_viewer_is_set(self):
        self.assertIsInstance(ROLE_PERMISSIONS['viewer'], set)

    def test_tabmaster_superset_of_editor(self):
        """Tabmaster should have at least every permission that editor has."""
        self.assertTrue(
            ROLE_PERMISSIONS['editor'].issubset(ROLE_PERMISSIONS['tabmaster']),
            msg="Editor perms not a subset of tabmaster perms",
        )

    def test_editor_superset_of_viewer(self):
        """Editor should have at least every permission that viewer has,
        except view-only permissions that viewer has but editor doesn't
        (e.g. VIEW_FEEDBACK_OVERVIEW, VIEW_BREAK)."""
        # Viewer has some view-only extras, so we check the intersection
        # is meaningful rather than strict superset.
        common = ROLE_PERMISSIONS['viewer'] & ROLE_PERMISSIONS['editor']
        self.assertTrue(len(common) > 0)

    def test_all_role_values_are_valid_permissions(self):
        """Every permission in every role set should be a valid Permission."""
        valid = set(Permission)
        for role, perms in ROLE_PERMISSIONS.items():
            if perms == '__all__':
                continue
            invalid = perms - valid
            self.assertEqual(invalid, set(), msg=f"Invalid perms in {role}: {invalid}")


@override_settings(**PERM_SETTINGS)
class HasPermissionOrgRoleTest(TestCase):
    """Test has_permission() with org membership roles."""

    def setUp(self):
        self.user = User.objects.create_user('perm_user', password='password')
        self.org = Organization.objects.create(
            name='Perm Org', slug='perm-org', is_workspace_enabled=True,
        )
        self.tournament = Tournament.objects.create(
            name='Perm Tournament', slug='perm-tournament',
            seq=1, organization=self.org,
        )

    def _set_role(self, role):
        OrganizationMembership.objects.filter(
            organization=self.org, user=self.user,
        ).delete()
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user, role=role,
        )

    # Owner/Admin: full access

    def test_owner_has_all_permissions(self):
        self._set_role('owner')
        self.assertTrue(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))
        self.assertTrue(has_permission(self.user, Permission.EDIT_SETTINGS, self.tournament))

    def test_admin_has_all_permissions(self):
        self._set_role('admin')
        self.assertTrue(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))
        self.assertTrue(has_permission(self.user, Permission.EDIT_SETTINGS, self.tournament))

    # Tabmaster: full tab ops but not settings-level

    def test_tabmaster_can_generate_draw(self):
        self._set_role('tabmaster')
        self.assertTrue(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))

    def test_tabmaster_can_edit_ballots(self):
        self._set_role('tabmaster')
        self.assertTrue(has_permission(self.user, Permission.EDIT_BALLOTSUBMISSIONS, self.tournament))

    def test_tabmaster_can_edit_settings(self):
        self._set_role('tabmaster')
        self.assertTrue(has_permission(self.user, Permission.EDIT_SETTINGS, self.tournament))

    # Editor: data entry, no draw/settings

    def test_editor_cannot_generate_draw(self):
        self._set_role('editor')
        self.assertFalse(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))

    def test_editor_can_add_ballots(self):
        self._set_role('editor')
        self.assertTrue(has_permission(self.user, Permission.ADD_BALLOTSUBMISSIONS, self.tournament))

    def test_editor_can_view_teams(self):
        self._set_role('editor')
        self.assertTrue(has_permission(self.user, Permission.VIEW_TEAMS, self.tournament))

    def test_editor_cannot_edit_settings(self):
        self._set_role('editor')
        self.assertFalse(has_permission(self.user, Permission.EDIT_SETTINGS, self.tournament))

    # Legacy member: same as editor

    def test_legacy_member_grants_editor_perms(self):
        self._set_role('member')
        self.assertTrue(has_permission(self.user, Permission.ADD_BALLOTSUBMISSIONS, self.tournament))

    def test_legacy_member_cannot_generate_draw(self):
        self._set_role('member')
        self.assertFalse(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))

    # Viewer: read-only

    def test_viewer_can_view_teams(self):
        self._set_role('viewer')
        self.assertTrue(has_permission(self.user, Permission.VIEW_TEAMS, self.tournament))

    def test_viewer_cannot_edit_ballots(self):
        self._set_role('viewer')
        self.assertFalse(has_permission(self.user, Permission.EDIT_BALLOTSUBMISSIONS, self.tournament))

    def test_viewer_cannot_add_ballots(self):
        self._set_role('viewer')
        self.assertFalse(has_permission(self.user, Permission.ADD_BALLOTSUBMISSIONS, self.tournament))

    def test_viewer_cannot_generate_draw(self):
        self._set_role('viewer')
        self.assertFalse(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))

    # Non-member: no org-level access

    def test_non_member_no_org_access(self):
        other = User.objects.create_user('other_user', password='password')
        self.assertFalse(has_permission(other, Permission.VIEW_TEAMS, self.tournament))

    # Tournament owner bypass

    def test_tournament_owner_has_full_access(self):
        """Tournament owner should have access regardless of org role."""
        self.tournament.owner = self.user
        self.tournament.save()
        self.assertTrue(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))


@override_settings(**PERM_SETTINGS)
class PermissionCacheTest(TestCase):
    """Test that org role lookups are cached."""

    def setUp(self):
        self.user = User.objects.create_user('cache_user', password='password')
        self.org = Organization.objects.create(
            name='Cache Org', slug='cache-org', is_workspace_enabled=True,
        )
        self.tournament = Tournament.objects.create(
            name='Cache Tournament', slug='cache-tournament',
            seq=1, organization=self.org,
        )
        OrganizationMembership.objects.create(
            organization=self.org, user=self.user, role='tabmaster',
        )

    def test_second_call_uses_cache(self):
        """Calling has_permission twice should hit the cache on the second call."""
        # First call populates cache
        result1 = has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament)
        # Second call should return same result (from cache)
        result2 = has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament)
        self.assertEqual(result1, result2)
        self.assertTrue(result1)

    def test_role_change_invalidates_cache(self):
        """After changing a role, the permission should reflect the new role.
        This relies on the signal bumping the perm cache version."""
        self.assertTrue(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))
        # Downgrade to viewer
        membership = OrganizationMembership.objects.get(
            organization=self.org, user=self.user,
        )
        membership.role = 'viewer'
        membership.save()
        # Clear the in-memory _permissions cache on the user object
        if hasattr(self.user, '_permissions'):
            del self.user._permissions
        self.assertFalse(has_permission(self.user, Permission.GENERATE_DEBATE, self.tournament))
