"""Let site admins keep a tournament off the home page list.

Only the home page listing reads this; the tournament's own pages are not
affected. Defaults to False, so nothing disappears because of this migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0044_tournament_is_publicly_listed'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='hidden_from_home',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Keeps this tournament off the home page list, even if it '
                    'would otherwise be listed or featured. Its pages stay '
                    'exactly as visible as before.'
                ),
                verbose_name='hidden from the home page',
            ),
        ),
    ]
