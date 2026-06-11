"""Add OrgAnalyticsSummary model for hourly per-org analytics aggregation."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_pageview_org_slug_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrgAnalyticsSummary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('org_slug', models.CharField(db_index=True, max_length=80, verbose_name='org slug')),
                ('date', models.DateField(db_index=True, verbose_name='date')),
                ('hour', models.SmallIntegerField(verbose_name='hour (UTC)')),
                ('page_views', models.PositiveIntegerField(default=0, verbose_name='page views')),
                ('unique_paths', models.JSONField(blank=True, default=list, verbose_name='unique paths')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='last updated')),
            ],
            options={
                'verbose_name': 'org analytics summary',
                'verbose_name_plural': 'org analytics summaries',
                'ordering': ['-date', '-hour'],
            },
        ),
        migrations.AddConstraint(
            model_name='organalyticssummary',
            constraint=models.UniqueConstraint(
                fields=['org_slug', 'date', 'hour'],
                name='analytics_orgsum_org_date_hour_uniq',
            ),
        ),
        migrations.AddIndex(
            model_name='organalyticssummary',
            index=models.Index(fields=['org_slug', 'date'], name='analytics_orgsum_slug_date_idx'),
        ),
    ]
