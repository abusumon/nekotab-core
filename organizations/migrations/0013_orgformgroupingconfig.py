# Reconstructed to match the live production schema for
# organizations_orgformgroupingconfig (migration was applied in the DB on
# 2026-06-03 but its file was never committed; see recovery 2026-06-06).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0012_add_org_registration'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrgFormGroupingConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group_by_field_id', models.CharField(blank=True, default='', help_text='Id of the form field whose value responses are grouped by.', max_length=100, verbose_name='group-by field id')),
                ('display_field_ids', models.JSONField(blank=True, default=list, help_text='Ordered list of field ids shown for each grouped response.', verbose_name='display field ids')),
                ('display_title', models.CharField(blank=True, default='', max_length=200, verbose_name='display title')),
                ('only_confirmed', models.BooleanField(default=True, help_text='When on, only confirmed responses appear on the grouped board.', verbose_name='only confirmed')),
                ('form', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='grouping_config', to='organizations.orgform', verbose_name='form')),
            ],
            options={
                'verbose_name': 'form grouping config',
                'verbose_name_plural': 'form grouping configs',
            },
        ),
    ]
