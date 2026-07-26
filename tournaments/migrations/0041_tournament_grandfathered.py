"""Snapshot which tournaments predate NekoTab Premium, instead of inferring it.

Grandfathering used to be a date comparison against ``settings.PREMIUM_LAUNCH_AT``.
That made one environment variable the only thing standing between 550+ live
tournaments and a paywall: set it a day late and tournaments that should be free
start demanding payment; set it wrong in a way nobody notices and the error is
silent until a director is locked out mid-competition. It also depended on
``created_at``, which is nullable on rows that predate that column.

This records the answer once, as a fact, at the moment of the migration. After
this runs, nothing about grandfathering can drift: the set is fixed in the
database and no configuration change can alter it.

The AddField and the backfill are deliberately in ONE migration so they share a
transaction. Split across two, there is a committed window in which the column
exists and every pre-existing tournament reads ``grandfathered=False`` — which is
to say, a window in which the entire back catalogue is paywalled.
"""

from django.db import migrations, models


def grandfather_existing_tournaments(apps, schema_editor):
    """Flag every tournament that exists right now as free forever.

    Idempotent. Re-running is a no-op, because the only state that matters —
    "has this already been applied?" — is readable from the data itself: if any
    row is flagged, the snapshot has been taken and must not be retaken. Without
    that guard, running this a second time later would sweep up every tournament
    created since launch and give away paid access to all of them.

    The one case this cannot defend against is a full reverse of this migration
    (which drops the column, destroying the snapshot) followed by a re-apply.
    That is not recoverable by any guard here — restore from a backup instead.
    """
    Tournament = apps.get_model('tournaments', 'Tournament')

    if Tournament.objects.filter(grandfathered=True).exists():
        return

    Tournament.objects.update(grandfathered=True)


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0040_tournamentmetadata_tournamentauditlog_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='grandfathered',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Set on every tournament that already existed when NekoTab '
                    'Premium launched. These are free forever and are never '
                    'paywalled. Set once by a data migration — do not set it by '
                    'hand to give away access; record a payment instead.'
                ),
                verbose_name='grandfathered (free forever)',
            ),
        ),
        migrations.RunPython(
            grandfather_existing_tournaments,
            # Reversing must not un-grandfather anybody. The AddField reversal
            # drops the column outright, so there is nothing useful to undo here
            # and plenty to get wrong.
            migrations.RunPython.noop,
            elidable=False,
        ),
    ]
