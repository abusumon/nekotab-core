"""Permanent record of demo tournaments created, for the lifetime allowance.

The allowance has to be counted from something that outlives the tournament.
Demos delete themselves within hours, so counting rows in ``tournaments`` would
reset the tally every afternoon and could never enforce a limit described as
"lifetime".

The backfill exists for the case where demo tournaments were created between
the 0042 deploy and this one. On a database where the demo feature has not
shipped yet it is a no-op, and it is safe to re-run either way.
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_existing_demos(apps, schema_editor):
    """Record any demo tournaments that already exist and are not yet logged.

    Idempotent: keyed on the tournament FK, so a demo that already has a log
    row is skipped rather than double-counted against its owner's allowance.
    """
    Tournament = apps.get_model('tournaments', 'Tournament')
    DemoTournamentLog = apps.get_model('tournaments', 'DemoTournamentLog')

    logged = set(
        DemoTournamentLog.objects.filter(tournament__isnull=False)
        .values_list('tournament_id', flat=True),
    )
    rows = [
        DemoTournamentLog(user_id=t.owner_id, tournament_id=t.pk, slug=t.slug)
        for t in Tournament.objects.filter(is_demo=True, owner__isnull=False)
        if t.pk not in logged
    ]
    if rows:
        DemoTournamentLog.objects.bulk_create(rows)


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0042_tournament_demo'),
        migrations.swappable_dependency('auth.User'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemoTournamentLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('slug', models.CharField(
                    blank=True, default='', max_length=100,
                    help_text="The demo's slug, kept after the tournament is deleted.",
                    verbose_name='slug')),
                ('created_at', models.DateTimeField(
                    auto_now_add=True, db_index=True, verbose_name='created at')),
                ('tournament', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='demo_log_entries',
                    to='tournaments.tournament',
                    help_text='Cleared when the demo is deleted; the row itself remains.',
                    verbose_name='tournament')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='demo_tournament_logs',
                    to='auth.user',
                    verbose_name='user')),
            ],
            options={
                'verbose_name': 'demo tournament log',
                'verbose_name_plural': 'demo tournament logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='demotournamentlog',
            index=models.Index(fields=['user', 'created_at'],
                               name='tournaments_demolog_user_idx'),
        ),
        migrations.RunPython(backfill_existing_demos, migrations.RunPython.noop),
    ]
