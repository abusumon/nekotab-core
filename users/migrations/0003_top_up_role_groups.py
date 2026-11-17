"""Role groups store a snapshot of their permissions, taken when the
tournament was created. Add any permissions their standard role has gained
since, so e.g. an old "Tabulation Director" group is no longer missing pages.
Only adds permissions; never removes any."""
from django.db import migrations


def top_up(apps, schema_editor):
    from users.groups import all_groups
    Group = apps.get_model('users', 'Group')
    presets = {str(g.name): [str(p) for p in g.permissions] for g in all_groups()}
    for group in Group.objects.filter(name__in=presets.keys()).iterator():
        have = list(group.permissions or [])
        missing = [p for p in presets[group.name] if p not in have]
        if missing:
            group.permissions = have + missing
            group.save(update_fields=['permissions'])


class Migration(migrations.Migration):
    dependencies = [('users', '0002_group_users_alter_group_permissions_and_more')]
    operations = [migrations.RunPython(top_up, migrations.RunPython.noop)]
