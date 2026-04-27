"""Enforce NOT NULL on Tournament.organization.

Pre-condition: migration 0038 has backfilled all existing tournaments.
Run `python manage.py check_tenant_integrity` before deploying this migration
to verify that no tournaments have organization=NULL.

Safe deployment strategy:
1. Deploy code with this migration in the queue (but don't migrate yet).
2. Run `python manage.py shell` in production and execute:
       from tournaments.models import Tournament
       assert Tournament.objects.filter(organization__isnull=True).count() == 0
3. Run `python manage.py migrate tournaments 0039`
4. Verify: `python manage.py check --deploy`
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0038_backfill_tournament_orgs'),
        ('organizations', '0001_create_organization_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournament',
            name='organization',
            field=models.ForeignKey(
                to='organizations.Organization',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='tournaments',
                verbose_name='organization',
                help_text=(
                    'The organization this tournament belongs to. '
                    'All org members get access based on their org role.'
                ),
            ),
        ),
    ]
