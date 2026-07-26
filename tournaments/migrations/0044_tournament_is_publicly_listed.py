"""Whether a tournament is featured in the public home-page showcase.

Separate from ``is_listed``, which controls whether a stranger may *read* the
tournament at all. This one controls whether we *advertise* it. Defaults to
False, so nothing becomes featured as a side effect of this migration — every
showcased tournament is there because somebody turned it on.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0043_demotournamentlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='is_publicly_listed',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text=(
                    'If enabled, this tournament appears in the public showcase '
                    'on the NekoTab home page. Demo tournaments are never '
                    'shown, whatever this says.'
                ),
                verbose_name='featured on the home page',
            ),
        ),
    ]
