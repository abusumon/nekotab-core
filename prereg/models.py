import uuid
import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tournaments.models import Tournament

logger = logging.getLogger(__name__)


class FormType(models.TextChoices):
    TEAM_PREREG = 'team_prereg', _('Team Pre-Registration')
    ADJ_INDEPENDENT = 'adj_independent', _('Independent Adjudicator')


class FieldType(models.TextChoices):
    TEXT = 'text', _('Short Text')
    TEXTAREA = 'textarea', _('Long Text')
    EMAIL = 'email', _('Email')
    PHONE = 'phone', _('Phone Number')
    NUMBER = 'number', _('Number')
    RADIO = 'radio', _('Single Choice (Radio)')
    CHECKBOXES = 'checkboxes', _('Multiple Choice (Checkboxes)')
    SELECT = 'select', _('Dropdown')


class SubmissionStatus(models.TextChoices):
    PENDING = 'pending', _('Pending Review')
    OFFERED = 'offered', _('Slot Offered')
    CONFIRMED = 'confirmed', _('Payment Confirmed')
    REJECTED = 'rejected', _('Not Selected')


def _default_team_fields():
    return [
        {'order': 1, 'label': 'Team Name', 'field_type': 'text', 'required': True, 'is_name_field': True},
        {'order': 2, 'label': 'Team Representative Name', 'field_type': 'text', 'required': True},
        {'order': 3, 'label': 'Club / Institution Name', 'field_type': 'text', 'required': True},
        {'order': 4, 'label': 'Representative Email', 'field_type': 'email', 'required': True, 'is_email_field': True},
        {'order': 5, 'label': 'Representative Contact Number', 'field_type': 'phone', 'required': True},
        {'order': 6, 'label': 'Alternative Contact Number', 'field_type': 'phone', 'required': False},
        {'order': 7, 'label': 'Representative Facebook Profile Link', 'field_type': 'text', 'required': False},
        {'order': 8, 'label': 'How many slots are you requesting?', 'field_type': 'radio', 'required': True,
         'options_text': '1\n2\n3'},
        {'order': 9, 'label': 'Any comments or feedback?', 'field_type': 'textarea', 'required': False},
    ]


def _default_adj_fields():
    return [
        {'order': 1, 'label': 'Email', 'field_type': 'email', 'required': True, 'is_email_field': True},
        {'order': 2, 'label': 'Full Name', 'field_type': 'text', 'required': True, 'is_name_field': True},
        {'order': 3, 'label': 'Institution Name', 'field_type': 'text', 'required': True},
        {'order': 4, 'label': 'Contact Number', 'field_type': 'phone', 'required': True},
        {'order': 5, 'label': 'T-shirt Size', 'field_type': 'radio', 'required': True,
         'options_text': 'S\nM\nL\nXL\nXXL'},
        {'order': 6, 'label': 'Payment Method', 'field_type': 'radio', 'required': True,
         'options_text': 'Bkash 01749054820\nNagad 01749054820'},
        {'order': 7, 'label': 'Transaction ID', 'field_type': 'text', 'required': True},
        {'order': 8, 'label': 'Top 5 Achievements as Adjudicator', 'field_type': 'textarea', 'required': False},
    ]


def seed_default_fields(form):
    """Populate a freshly created PreRegForm with sensible default fields."""
    if form.form_type == FormType.TEAM_PREREG:
        defaults = _default_team_fields()
    else:
        defaults = _default_adj_fields()

    for d in defaults:
        PreRegFormField.objects.create(
            form=form,
            label=d['label'],
            field_type=d['field_type'],
            required=d.get('required', False),
            options_text=d.get('options_text', ''),
            order=d['order'],
            is_email_field=d.get('is_email_field', False),
            is_name_field=d.get('is_name_field', False),
        )


class PreRegForm(models.Model):
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='prereg_forms',
        verbose_name=_('tournament'),
    )
    form_type = models.CharField(
        max_length=20,
        choices=FormType.choices,
        verbose_name=_('form type'),
    )
    title = models.CharField(max_length=255, verbose_name=_('title'))
    description = models.TextField(blank=True, verbose_name=_('description'))
    is_open = models.BooleanField(
        default=True,
        verbose_name=_('accepting submissions'),
        help_text=_('Uncheck to close the form to new submissions.'),
    )
    final_reg_url = models.URLField(
        blank=True,
        verbose_name=_('final registration URL'),
        help_text=_('URL sent to confirmed participants for final registration.'),
    )
    payment_instructions = models.TextField(
        blank=True,
        verbose_name=_('payment instructions'),
        help_text=_('Payment details included in the slot offer email.'),
    )
    allocations_published = models.BooleanField(
        default=False,
        verbose_name=_('allocations published'),
    )
    public_slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tournament', 'form_type')
        verbose_name = _('pre-registration form')
        verbose_name_plural = _('pre-registration forms')

    def __str__(self):
        return f"{self.tournament} — {self.get_form_type_display()}"


class PreRegFormField(models.Model):
    form = models.ForeignKey(
        PreRegForm,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name=_('form'),
    )
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        verbose_name=_('field type'),
    )
    label = models.CharField(max_length=255, verbose_name=_('label'))
    required = models.BooleanField(default=False, verbose_name=_('required'))
    placeholder = models.CharField(max_length=255, blank=True, verbose_name=_('placeholder'))
    options_text = models.TextField(
        blank=True,
        verbose_name=_('options (one per line)'),
        help_text=_('For radio/select/checkboxes: one option per line.'),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_('order'))
    is_email_field = models.BooleanField(
        default=False,
        verbose_name=_('is email field'),
        help_text=_("Mark as the respondent's email for sending notifications."),
    )
    is_name_field = models.BooleanField(
        default=False,
        verbose_name=_('is name / team name field'),
        help_text=_("Mark as the respondent's name or team name."),
    )

    class Meta:
        ordering = ['order', 'pk']
        verbose_name = _('form field')
        verbose_name_plural = _('form fields')

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"

    @property
    def options(self):
        if not self.options_text:
            return []
        return [o.strip() for o in self.options_text.splitlines() if o.strip()]


class PreRegSubmission(models.Model):
    form = models.ForeignKey(
        PreRegForm,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name=_('form'),
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_('submitted at'))
    respondent_email = models.EmailField(blank=True, verbose_name=_('email'))
    respondent_name = models.CharField(max_length=255, blank=True, verbose_name=_('name / team name'))
    data = models.JSONField(default=dict, verbose_name=_('response data'))
    status = models.CharField(
        max_length=20,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING,
        db_index=True,
        verbose_name=_('status'),
    )

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('submission')
        verbose_name_plural = _('submissions')

    def __str__(self):
        name = self.respondent_name or f"#{self.pk}"
        return f"{name} — {self.submitted_at:%Y-%m-%d %H:%M}"

    def get_field_value(self, field_id):
        val = self.data.get(str(field_id), '')
        if isinstance(val, list):
            return ', '.join(val)
        return val


class SlotAllocation(models.Model):
    submission = models.OneToOneField(
        PreRegSubmission,
        on_delete=models.CASCADE,
        related_name='slot',
        verbose_name=_('submission'),
    )
    slots_granted = models.PositiveSmallIntegerField(default=0, verbose_name=_('slots granted'))
    notes = models.TextField(blank=True, verbose_name=_('internal notes'))
    include_in_public = models.BooleanField(
        default=True,
        verbose_name=_('include in public allocation list'),
    )
    offer_email_sent = models.BooleanField(default=False, verbose_name=_('offer email sent'))
    offer_email_sent_at = models.DateTimeField(null=True, blank=True)
    payment_confirmed = models.BooleanField(default=False, verbose_name=_('payment confirmed'))
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)
    final_reg_email_sent = models.BooleanField(default=False, verbose_name=_('final reg email sent'))
    final_reg_email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('slot allocation')
        verbose_name_plural = _('slot allocations')

    def __str__(self):
        return f"{self.submission} — {self.slots_granted} slot(s)"
