"""Demo tournaments: throwaway, never paywalled, deleted a few hours later.

Both columns are indexed. ``is_demo`` because every premium check and every
public listing query filters on it, and ``expires_at`` because the cleanup task
runs on a schedule and its query — expired demos — must not degrade into a full
table scan as the tournament table grows.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0041_tournament_grandfathered'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='is_demo',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text=(
                    'A throwaway tournament for trying NekoTab out. Never '
                    'paywalled, never publicly listed, and deleted '
                    'automatically once expires_at passes.'
                ),
                verbose_name='demo tournament',
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='expires_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                db_index=True,
                help_text=(
                    'When this tournament is automatically deleted. Only set '
                    'on demo tournaments.'
                ),
                verbose_name='expires at',
            ),
        ),
    ]
