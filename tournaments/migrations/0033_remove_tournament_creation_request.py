from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0032_tournamentcreationrequest'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TournamentCreationRequest',
        ),
    ]
