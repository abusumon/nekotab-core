from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': 'nekotab.app',
            'name': 'NekoTab',
        },
    )


def revert_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.filter(id=1).update(
        domain='example.com',
        name='example.com',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0004_add_more_articles'),
        ('sites', '0002_alter_domain_unique'),
    ]
    operations = [
        migrations.RunPython(set_site_domain, revert_site_domain),
    ]
