"""Rounds can release their draw to participants only (NekoTab Pro)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0045_tournament_hidden_from_home'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='draw_teams_only',
            field=models.BooleanField(
                default=False,
                help_text=('When the draw is released, keep it off the public pages: only participants see it, '
                           'through their private URLs and the messages sent to them.'),
                verbose_name='draw released to participants only',
            ),
        ),
    ]
