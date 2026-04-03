"""Data migration: users who own more than one active org keep only the oldest;
the rest are marked is_active=False with an explanatory deactivation_reason.
"""
from django.db import migrations


def deactivate_duplicate_owner_orgs(apps, schema_editor):
    OrganizationMembership = apps.get_model('organizations', 'OrganizationMembership')
    Organization = apps.get_model('organizations', 'Organization')

    # Collect all owner memberships grouped by user
    from collections import defaultdict
    owner_memberships = (
        OrganizationMembership.objects
        .filter(role='owner')
        .select_related('organization', 'user')
        .order_by('organization__created_at')
    )

    user_orgs = defaultdict(list)
    for m in owner_memberships:
        if m.organization.is_active:
            user_orgs[m.user_id].append(m.organization)

    deactivated = 0
    for user_id, orgs in user_orgs.items():
        if len(orgs) <= 1:
            continue
        # Keep the oldest (first); deactivate the rest
        for org in orgs[1:]:
            org.is_active = False
            org.deactivation_reason = (
                "Automatically deactivated: one-workspace-per-user limit "
                "enforced during migration. Oldest workspace retained."
            )
            org.save()
            deactivated += 1

    if deactivated:
        print(f"\n  Deactivated {deactivated} duplicate owner org(s).")


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0003_add_is_active_fields'),
    ]

    operations = [
        migrations.RunPython(
            deactivate_duplicate_owner_orgs,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
