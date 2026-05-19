import datetime
import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import utils.models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0004_deactivate_duplicate_owner_orgs'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ClubMemberProfile
        migrations.CreateModel(
            name='ClubMemberProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, default='', max_length=30, verbose_name='phone')),
                ('department', models.CharField(blank=True, default='', max_length=100, verbose_name='department')),
                ('batch', models.CharField(blank=True, default='', help_text="e.g. '2023–2024' or 'Spring 2024'", max_length=50, verbose_name='batch / session')),
                ('designation', models.CharField(blank=True, default='', help_text="e.g. 'Best Speaker finalist', 'Club President', 'Coach'", max_length=100, verbose_name='designation')),
                ('bio', models.TextField(blank=True, default='', verbose_name='bio')),
                ('membership', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to='organizations.organizationmembership',
                    verbose_name='membership',
                )),
            ],
            options={
                'verbose_name': 'club member profile',
                'verbose_name_plural': 'club member profiles',
            },
        ),

        # OrganizationInvitation
        migrations.CreateModel(
            name='OrganizationInvitation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='token')),
                ('email', models.EmailField(verbose_name='email')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('role', models.CharField(
                    choices=[
                        ('owner', 'Owner'), ('admin', 'Admin'), ('tabmaster', 'Tabmaster'),
                        ('editor', 'Editor'), ('viewer', 'Viewer'), ('member', 'Member'),
                    ],
                    default='viewer', max_length=20, verbose_name='role',
                )),
                ('phone', models.CharField(blank=True, default='', max_length=30, verbose_name='phone')),
                ('department', models.CharField(blank=True, default='', max_length=100, verbose_name='department')),
                ('batch', models.CharField(blank=True, default='', max_length=50, verbose_name='batch')),
                ('designation', models.CharField(blank=True, default='', max_length=100, verbose_name='designation')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('expires_at', models.DateTimeField(verbose_name='expires at')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='accepted at')),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invitations',
                    to='organizations.organization',
                    verbose_name='organization',
                )),
                ('invited_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_org_invitations',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='invited by',
                )),
                ('accepted_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='accepted_org_invitations',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='accepted by',
                )),
            ],
            options={
                'verbose_name': 'organization invitation',
                'verbose_name_plural': 'organization invitations',
            },
        ),

        migrations.AddIndex(
            model_name='organizationinvitation',
            index=models.Index(fields=['organization', 'accepted_at'], name='org_inv_org_accepted_idx'),
        ),
        migrations.AddIndex(
            model_name='organizationinvitation',
            index=models.Index(fields=['email', 'organization'], name='org_inv_email_org_idx'),
        ),
    ]
