from django.db import connection, migrations


def forwards(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "INSERT INTO options_tournamentpreferencemodel (section, name, raw_value, instance_id) "
        "SELECT 'standings', 'speaker_standings_precedence', raw_value, instance_id "
        "FROM options_tournamentpreferencemodel WHERE section='standings' AND name='rank_speakers_by' "
        "ON CONFLICT DO NOTHING;"
    )
    schema_editor.execute(
        "DELETE FROM options_tournamentpreferencemodel WHERE section='standings' AND name='rank_speakers_by';"
    )


def backwards(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "INSERT INTO options_tournamentpreferencemodel (section, name, raw_value, instance_id) "
        "SELECT 'standings', 'rank_speakers_by', (string_to_array(raw_value, '//'))[1], instance_id "
        "FROM options_tournamentpreferencemodel WHERE section='standings' AND name='speaker_standings_precedence' "
        "ON CONFLICT DO NOTHING;"
    )
    schema_editor.execute(
        "DELETE FROM options_tournamentpreferencemodel WHERE section='standings' AND name='speaker_standings_precedence';"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('options', '0004_convert_tournament_staff'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
