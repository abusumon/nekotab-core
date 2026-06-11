from django.db import migrations, models


class Migration(migrations.Migration):
    """Add org_slug field and performance indexes to analytics_pageview."""

    dependencies = [
        ('analytics', '0002_alter_activesession_options_alter_dailystats_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageview',
            name='org_slug',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['org_slug', 'timestamp'], name='analytics_pv_org_slug_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='pageview',
            index=models.Index(fields=['timestamp'], name='analytics_pv_ts_idx'),
        ),
    ]
