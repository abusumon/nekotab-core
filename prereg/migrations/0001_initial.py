import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreRegForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_type', models.CharField(
                    choices=[('team_prereg', 'Team Pre-Registration'), ('adj_independent', 'Independent Adjudicator')],
                    max_length=20,
                    verbose_name='form type',
                )),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('is_open', models.BooleanField(
                    default=True,
                    help_text='Uncheck to close the form to new submissions.',
                    verbose_name='accepting submissions',
                )),
                ('final_reg_url', models.URLField(
                    blank=True,
                    help_text='URL sent to confirmed participants for final registration.',
                    verbose_name='final registration URL',
                )),
                ('payment_instructions', models.TextField(
                    blank=True,
                    help_text='Payment details included in the slot offer email.',
                    verbose_name='payment instructions',
                )),
                ('allocations_published', models.BooleanField(default=False, verbose_name='allocations published')),
                ('public_slug', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='prereg_forms',
                    to='tournaments.tournament',
                    verbose_name='tournament',
                )),
            ],
            options={
                'verbose_name': 'pre-registration form',
                'verbose_name_plural': 'pre-registration forms',
                'unique_together': {('tournament', 'form_type')},
            },
        ),
        migrations.CreateModel(
            name='PreRegFormField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_type', models.CharField(
                    choices=[
                        ('text', 'Short Text'), ('textarea', 'Long Text'), ('email', 'Email'),
                        ('phone', 'Phone Number'), ('number', 'Number'),
                        ('radio', 'Single Choice (Radio)'), ('checkboxes', 'Multiple Choice (Checkboxes)'),
                        ('select', 'Dropdown'),
                    ],
                    max_length=20,
                    verbose_name='field type',
                )),
                ('label', models.CharField(max_length=255, verbose_name='label')),
                ('required', models.BooleanField(default=False, verbose_name='required')),
                ('placeholder', models.CharField(blank=True, max_length=255, verbose_name='placeholder')),
                ('options_text', models.TextField(
                    blank=True,
                    help_text='For radio/select/checkboxes: one option per line.',
                    verbose_name='options (one per line)',
                )),
                ('order', models.PositiveIntegerField(default=0, verbose_name='order')),
                ('is_email_field', models.BooleanField(
                    default=False,
                    help_text="Mark as the respondent's email for sending notifications.",
                    verbose_name='is email field',
                )),
                ('is_name_field', models.BooleanField(
                    default=False,
                    help_text="Mark as the respondent's name or team name.",
                    verbose_name='is name / team name field',
                )),
                ('form', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fields',
                    to='prereg.preregform',
                    verbose_name='form',
                )),
            ],
            options={
                'verbose_name': 'form field',
                'verbose_name_plural': 'form fields',
                'ordering': ['order', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='PreRegSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submitted_at', models.DateTimeField(auto_now_add=True, verbose_name='submitted at')),
                ('respondent_email', models.EmailField(blank=True, verbose_name='email')),
                ('respondent_name', models.CharField(blank=True, max_length=255, verbose_name='name / team name')),
                ('data', models.JSONField(default=dict, verbose_name='response data')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending Review'), ('offered', 'Slot Offered'),
                        ('confirmed', 'Payment Confirmed'), ('rejected', 'Not Selected'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                    verbose_name='status',
                )),
                ('form', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='submissions',
                    to='prereg.preregform',
                    verbose_name='form',
                )),
            ],
            options={
                'verbose_name': 'submission',
                'verbose_name_plural': 'submissions',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='SlotAllocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slots_granted', models.PositiveSmallIntegerField(default=0, verbose_name='slots granted')),
                ('notes', models.TextField(blank=True, verbose_name='internal notes')),
                ('include_in_public', models.BooleanField(default=True, verbose_name='include in public allocation list')),
                ('offer_email_sent', models.BooleanField(default=False, verbose_name='offer email sent')),
                ('offer_email_sent_at', models.DateTimeField(blank=True, null=True)),
                ('payment_confirmed', models.BooleanField(default=False, verbose_name='payment confirmed')),
                ('payment_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('final_reg_email_sent', models.BooleanField(default=False, verbose_name='final reg email sent')),
                ('final_reg_email_sent_at', models.DateTimeField(blank=True, null=True)),
                ('submission', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='slot',
                    to='prereg.preregsubmission',
                    verbose_name='submission',
                )),
            ],
            options={
                'verbose_name': 'slot allocation',
                'verbose_name_plural': 'slot allocations',
            },
        ),
    ]
