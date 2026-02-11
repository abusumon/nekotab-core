# Generated manually for campaigns app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Internal campaign name for your reference', max_length=200)),
                ('subject', models.CharField(help_text='Email subject line', max_length=200)),
                ('preview_text', models.CharField(blank=True, help_text='Preview text shown in inbox (optional)', max_length=200)),
                ('html_content', models.TextField(help_text='HTML content of the email')),
                ('plain_text_content', models.TextField(blank=True, help_text='Plain text version (auto-generated if empty)')),
                ('send_to_all', models.BooleanField(default=True, help_text='Send to all users with email addresses')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('total_recipients', models.PositiveIntegerField(default=0)),
                ('successful_sends', models.PositiveIntegerField(default=0)),
                ('failed_sends', models.PositiveIntegerField(default=0)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Email Campaign',
                'verbose_name_plural': 'Email Campaigns',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EmailTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('html_content', models.TextField()),
                ('thumbnail', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CampaignRecipient',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('bounced', 'Bounced')], default='pending', max_length=20)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipients', to='campaigns.emailcampaign')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-sent_at'],
                'unique_together': {('campaign', 'email')},
            },
        ),
    ]
