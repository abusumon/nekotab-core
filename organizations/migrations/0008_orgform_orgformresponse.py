from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0007_clubmember'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrgForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('slug', models.SlugField(max_length=80, verbose_name='slug')),
                ('category', models.CharField(
                    choices=[
                        ('pre_reg', 'Pre-Registration'),
                        ('registration', 'Registration'),
                        ('volunteer', 'Volunteer'),
                        ('indep_adj', 'Independent Adjudicator'),
                        ('recruitment', 'Member Recruitment'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=20,
                    verbose_name='category',
                )),
                ('fields', models.JSONField(blank=True, default=list, verbose_name='fields')),
                ('is_accepting', models.BooleanField(default=False, verbose_name='accepting submissions')),
                ('is_confirmation_public', models.BooleanField(default=False, verbose_name='confirmation board public')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='forms',
                    to='organizations.organization',
                    verbose_name='organization',
                )),
            ],
            options={
                'verbose_name': 'organization form',
                'verbose_name_plural': 'organization forms',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrgFormResponse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(default=dict, verbose_name='submitted data')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('confirmed', 'Confirmed'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='status',
                )),
                ('confirmed_slots', models.PositiveIntegerField(blank=True, null=True, verbose_name='confirmed slots')),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('form', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='responses',
                    to='organizations.orgform',
                    verbose_name='form',
                )),
            ],
            options={
                'verbose_name': 'form response',
                'verbose_name_plural': 'form responses',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='orgform',
            constraint=models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_orgform_org_slug',
            ),
        ),
    ]
