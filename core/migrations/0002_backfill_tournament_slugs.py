"""Backfill SubdomainSlugReservation rows for every existing tournament.

This ensures the slug reservation table is consistent with all tournaments
that existed before the core app was introduced.
"""

from django.db import migrations


def backfill(apps, schema_editor):
    Tournament = apps.get_model('tournaments', 'Tournament')
    SubdomainSlugReservation = apps.get_model('core', 'SubdomainSlugReservation')
    for t in Tournament.objects.all():
        SubdomainSlugReservation.objects.get_or_create(
            slug=t.slug.lower(),
            defaults={
                'tenant_type': 'tournament',
                'tournament': t,
                'organization': None,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('tournaments', '0039_enforce_organization_not_null'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
