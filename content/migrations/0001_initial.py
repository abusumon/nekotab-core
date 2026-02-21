from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(blank=True, help_text='Emoji icon', max_length=10)),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name_plural': 'Article Categories',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=220, unique=True)),
                ('summary', models.TextField(help_text='Short description shown in listings and meta tags (max 500 chars).', max_length=500)),
                ('body', models.TextField(blank=True, help_text='Article body (HTML allowed, will be sanitized on render).')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')], db_index=True, default='draft', max_length=10)),
                ('reading_time_minutes', models.PositiveSmallIntegerField(default=1, help_text='Estimated reading time in minutes.')),
                ('meta_title', models.CharField(blank=True, help_text='Override title tag', max_length=70)),
                ('meta_description', models.CharField(blank=True, help_text='Override meta description', max_length=160)),
                ('related_format_slugs', models.JSONField(blank=True, default=list, help_text='List of debate format identifiers (e.g. ["bp","australs"]) for cross-linking from tournament pages.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles', to='content.articlecategory')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['status', '-created_at'], name='content_art_status_fc7162_idx'),
                    models.Index(fields=['slug'], name='content_art_slug_d82f31_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='TournamentContentBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('about_text', models.TextField(blank=True, help_text='About this tournament (shown on public page, max 2000 chars).')),
                ('host_organization', models.CharField(blank=True, max_length=200)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('format_description', models.CharField(blank=True, help_text='e.g. British Parliamentary, Australs 3v3', max_length=100)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('status_label', models.CharField(blank=True, help_text='e.g. Completed, In Progress, Upcoming', max_length=50)),
                ('meta_title', models.CharField(blank=True, max_length=70)),
                ('meta_description', models.CharField(blank=True, max_length=160)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='content_block', to='tournaments.tournament')),
            ],
            options={
                'verbose_name': 'Tournament Content Block',
            },
        ),
    ]
