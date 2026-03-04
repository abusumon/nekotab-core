from django.db import connection, migrations


def forwards(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "INSERT INTO options_tournamentpreferencemodel (section, name, raw_value, instance_id) "
        "SELECT section, new_pref, raw_value, instance_id FROM options_tournamentpreferencemodel, "
        "(VALUES ('ballots_per_debate_prelim'), ('ballots_per_debate_elim')) t(new_pref) "
        "WHERE section='debate_rules' AND name='ballots_per_debate' ON CONFLICT DO NOTHING;"
    )
    schema_editor.execute(
        "DELETE FROM options_tournamentpreferencemodel WHERE section='debate_rules' AND name='ballots_per_debate';"
    )


def backwards(apps, schema_editor):
    if connection.vendor != 'postgresql':
        return
    schema_editor.execute(
        "INSERT INTO options_tournamentpreferencemodel (section, name, raw_value, instance_id) "
        "SELECT section, name, raw_value, instance_id FROM options_tournamentpreferencemodel "
        "WHERE section='debate_rules' AND name='ballots_per_debate_prelim';"
    )
    schema_editor.execute(
        "DELETE FROM options_tournamentpreferencemodel WHERE section='debate_rules' "
        "AND name IN ('ballots_per_debate_prelim', 'ballots_per_debate_elim');"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('options', '0002_move_welcome_message'),
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
