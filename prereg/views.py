import logging

from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from tournaments.mixins import PublicTournamentPageMixin, TournamentMixin
from utils.mixins import AdministratorMixin

from .models import (
    FormType, SubmissionStatus, FieldType,
    PreRegForm, PreRegFormField, PreRegSubmission, SlotAllocation,
    seed_default_fields,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Helpers
# ==============================================================================

def _get_or_create_form(tournament, form_type, title):
    """Get or create a PreRegForm, seeding default fields on first creation."""
    form, created = PreRegForm.objects.get_or_create(
        tournament=tournament,
        form_type=form_type,
        defaults={'title': title, 'final_reg_url': 'https://kuddt.nekotab.app/'},
    )
    if created:
        seed_default_fields(form)
    return form


def _render_field_errors(fields, post_data):
    """Validate POST data against form fields; return (data_dict, errors)."""
    data = {}
    errors = {}
    for field in fields:
        key = f"field_{field.pk}"
        value = post_data.getlist(key) if field.field_type == FieldType.CHECKBOXES else post_data.get(key, '').strip()
        if field.required:
            if not value or value == []:
                errors[field.pk] = _("This field is required.")
        data[str(field.pk)] = value
    return data, errors


# ==============================================================================
# Public views
# ==============================================================================

class PublicPreRegFormView(PublicTournamentPageMixin, TemplateView):
    """Public team pre-registration form."""
    template_name = 'prereg/public_form.html'
    form_type = FormType.TEAM_PREREG
    public_page_preference = None  # always enabled; override check below

    def is_page_enabled(self, tournament):
        return True

    def get_prereg_form(self):
        return get_object_or_404(
            PreRegForm,
            tournament=self.tournament,
            form_type=self.form_type,
        )

    def get(self, request, *args, **kwargs):
        prereg_form = self.get_prereg_form()
        fields = list(prereg_form.fields.all())
        return self.render_to_response(self.get_context_data(
            prereg_form=prereg_form,
            form_fields=fields,
            field_values={},
            form_errors={},
        ))

    def post(self, request, *args, **kwargs):
        prereg_form = self.get_prereg_form()

        if not prereg_form.is_open:
            messages.error(request, _("This form is currently closed."))
            return redirect(request.path)

        fields = list(prereg_form.fields.all())
        data, errors = _render_field_errors(fields, request.POST)

        if errors:
            return self.render_to_response(self.get_context_data(
                prereg_form=prereg_form,
                form_fields=fields,
                field_values={str(f.pk): request.POST.getlist(f"field_{f.pk}") if f.field_type == FieldType.CHECKBOXES else request.POST.get(f"field_{f.pk}", '') for f in fields},
                form_errors=errors,
            ))

        # Extract email and name from tagged fields
        email = ''
        name = ''
        for field in fields:
            if field.is_email_field:
                email = data.get(str(field.pk), '')
            if field.is_name_field:
                name = data.get(str(field.pk), '')

        PreRegSubmission.objects.create(
            form=prereg_form,
            respondent_email=email,
            respondent_name=name,
            data=data,
        )

        return redirect('prereg-submission-success', tournament_slug=self.tournament.slug)


class PublicAdjRegFormView(PublicPreRegFormView):
    """Public independent adjudicator pre-registration form."""
    form_type = FormType.ADJ_INDEPENDENT


class SubmissionSuccessView(PublicTournamentPageMixin, TemplateView):
    template_name = 'prereg/submission_success.html'

    def is_page_enabled(self, tournament):
        return True


class PublicSlotsView(PublicTournamentPageMixin, TemplateView):
    """Beautiful public page showing confirmed slot allocations."""
    template_name = 'prereg/public_slots.html'

    def is_page_enabled(self, tournament):
        return True

    def get(self, request, *args, **kwargs):
        prereg_form = get_object_or_404(
            PreRegForm,
            tournament=self.tournament,
            form_type=FormType.TEAM_PREREG,
        )
        if not prereg_form.allocations_published:
            return self.render_to_response(self.get_context_data(
                prereg_form=prereg_form,
                allocations=[],
                not_published=True,
            ))

        allocations = (
            SlotAllocation.objects
            .filter(
                submission__form=prereg_form,
                include_in_public=True,
                slots_granted__gt=0,
            )
            .select_related('submission')
            .order_by('submission__respondent_name')
        )
        return self.render_to_response(self.get_context_data(
            prereg_form=prereg_form,
            allocations=allocations,
            not_published=False,
        ))


# ==============================================================================
# Admin views — Team Pre-Reg
# ==============================================================================

class PreRegAdminDashboardView(AdministratorMixin, TournamentMixin, TemplateView):
    """Admin dashboard: form builder + responses + slot allocation for team pre-reg."""
    template_name = 'prereg/admin/dashboard.html'
    view_permission = True

    def get(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = _get_or_create_form(t, FormType.TEAM_PREREG, f"{t.short_name} — Team Pre-Registration")
        fields = list(prereg_form.fields.all())
        submissions = list(
            prereg_form.submissions
            .prefetch_related('slot')
            .order_by('-submitted_at')
        )
        # Annotate each submission with its key field values for quick display
        key_fields = [f for f in fields if f.is_name_field or f.is_email_field]
        extra_fields = [f for f in fields if not f.is_name_field and not f.is_email_field][:4]

        return self.render_to_response(self.get_context_data(
            prereg_form=prereg_form,
            form_fields=fields,
            submissions=submissions,
            key_fields=key_fields,
            extra_fields=extra_fields,
            status_choices=SubmissionStatus.choices,
            field_type_choices=FieldType.choices,
        ))


class PreRegFormSettingsView(AdministratorMixin, TournamentMixin, View):
    """POST: update form settings."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.TEAM_PREREG)
        prereg_form.title = request.POST.get('title', prereg_form.title).strip()
        prereg_form.description = request.POST.get('description', '').strip()
        prereg_form.is_open = 'is_open' in request.POST
        prereg_form.payment_instructions = request.POST.get('payment_instructions', '').strip()
        prereg_form.final_reg_url = request.POST.get('final_reg_url', '').strip()
        prereg_form.save()
        messages.success(request, _("Form settings saved."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegAddFieldView(AdministratorMixin, TournamentMixin, View):
    """POST: add a field to the team pre-reg form."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.TEAM_PREREG)
        label = request.POST.get('label', '').strip()
        if not label:
            messages.error(request, _("Field label is required."))
            return redirect('prereg-admin-dashboard', tournament_slug=t.slug)

        field_type = request.POST.get('field_type', FieldType.TEXT)
        if field_type not in dict(FieldType.choices):
            field_type = FieldType.TEXT

        max_order = prereg_form.fields.aggregate(m=Max('order'))['m'] or 0
        PreRegFormField.objects.create(
            form=prereg_form,
            label=label,
            field_type=field_type,
            required='required' in request.POST,
            options_text=request.POST.get('options_text', '').strip(),
            placeholder=request.POST.get('placeholder', '').strip(),
            is_email_field='is_email_field' in request.POST,
            is_name_field='is_name_field' in request.POST,
            order=max_order + 1,
        )
        messages.success(request, _("Field added."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegDeleteFieldView(AdministratorMixin, TournamentMixin, View):
    """POST: delete a field from the team pre-reg form."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        field = get_object_or_404(
            PreRegFormField,
            pk=kwargs['field_pk'],
            form__tournament=t,
            form__form_type=FormType.TEAM_PREREG,
        )
        field.delete()
        messages.success(request, _("Field deleted."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegSaveAllocationsView(AdministratorMixin, TournamentMixin, View):
    """POST: bulk-save slot allocation data for team submissions."""
    view_permission = True

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.TEAM_PREREG)

        # Collect all submission IDs posted
        saved = 0
        for key, value in request.POST.items():
            if key.startswith('slots_'):
                try:
                    sub_pk = int(key.split('_', 1)[1])
                except (ValueError, IndexError):
                    continue
                sub = get_object_or_404(PreRegSubmission, pk=sub_pk, form=prereg_form)
                slots = int(value) if value.isdigit() else 0
                notes = request.POST.get(f'notes_{sub_pk}', '').strip()
                include_public = f'public_{sub_pk}' in request.POST

                slot, _ = SlotAllocation.objects.get_or_create(submission=sub)
                slot.slots_granted = slots
                slot.notes = notes
                slot.include_in_public = include_public
                slot.save()

                # Auto-update submission status
                if slots > 0 and sub.status == SubmissionStatus.PENDING:
                    sub.status = SubmissionStatus.OFFERED
                    sub.save(update_fields=['status'])
                elif slots == 0 and sub.status == SubmissionStatus.OFFERED:
                    sub.status = SubmissionStatus.PENDING
                    sub.save(update_fields=['status'])

                saved += 1

        messages.success(request, _(f"Slot allocations saved for {saved} submission(s)."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegPublishView(AdministratorMixin, TournamentMixin, View):
    """POST: toggle allocations_published on the team pre-reg form."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.TEAM_PREREG)
        prereg_form.allocations_published = not prereg_form.allocations_published
        prereg_form.save(update_fields=['allocations_published'])
        state = _("published") if prereg_form.allocations_published else _("unpublished")
        messages.success(request, _(f"Slot allocations {state}."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegSendOffersView(AdministratorMixin, TournamentMixin, View):
    """POST: send slot offer emails to selected submissions."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        prereg_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.TEAM_PREREG)

        selected_ids = request.POST.getlist('offer_ids')
        if not selected_ids:
            messages.warning(request, _("No submissions selected."))
            return redirect('prereg-admin-dashboard', tournament_slug=t.slug)

        sent = 0
        skipped = 0
        for sub_pk_str in selected_ids:
            try:
                sub_pk = int(sub_pk_str)
            except ValueError:
                continue

            sub = get_object_or_404(PreRegSubmission, pk=sub_pk, form=prereg_form)
            if not sub.respondent_email:
                skipped += 1
                continue

            try:
                slot = sub.slot
            except SlotAllocation.DoesNotExist:
                skipped += 1
                continue

            if slot.slots_granted < 1:
                skipped += 1
                continue

            subject = f"[{t.short_name}] Your slot offer — Action required"
            body = _build_offer_email_body(sub, slot, prereg_form, t)

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nekotab.app'),
                    recipient_list=[sub.respondent_email],
                    fail_silently=False,
                )
                slot.offer_email_sent = True
                slot.offer_email_sent_at = timezone.now()
                slot.save(update_fields=['offer_email_sent', 'offer_email_sent_at'])
                sub.status = SubmissionStatus.OFFERED
                sub.save(update_fields=['status'])
                sent += 1
            except Exception:
                logger.exception("Failed to send offer email to %s", sub.respondent_email)
                skipped += 1

        messages.success(request, _(f"Offer emails sent: {sent}. Skipped: {skipped}."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegConfirmPaymentView(AdministratorMixin, TournamentMixin, View):
    """POST: mark payment as confirmed for a submission."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        sub = get_object_or_404(PreRegSubmission, pk=kwargs['sub_pk'], form__tournament=t)
        slot, _ = SlotAllocation.objects.get_or_create(submission=sub)
        slot.payment_confirmed = True
        slot.payment_confirmed_at = timezone.now()
        slot.save(update_fields=['payment_confirmed', 'payment_confirmed_at'])
        sub.status = SubmissionStatus.CONFIRMED
        sub.save(update_fields=['status'])
        messages.success(request, _(f"Payment confirmed for {sub.respondent_name or sub.respondent_email}."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegSendFinalEmailView(AdministratorMixin, TournamentMixin, View):
    """POST: send final registration link email to a confirmed submission."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        sub = get_object_or_404(PreRegSubmission, pk=kwargs['sub_pk'], form__tournament=t)

        if not sub.respondent_email:
            messages.error(request, _("This submission has no email address."))
            return redirect('prereg-admin-dashboard', tournament_slug=t.slug)

        prereg_form = sub.form
        final_url = prereg_form.final_reg_url or 'https://kuddt.nekotab.app/'

        subject = f"[{t.short_name}] Complete your registration"
        body = _build_final_reg_email_body(sub, final_url, t)

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nekotab.app'),
                recipient_list=[sub.respondent_email],
                fail_silently=False,
            )
            slot, _ = SlotAllocation.objects.get_or_create(submission=sub)
            slot.final_reg_email_sent = True
            slot.final_reg_email_sent_at = timezone.now()
            slot.save(update_fields=['final_reg_email_sent', 'final_reg_email_sent_at'])
            messages.success(request, _(f"Final registration email sent to {sub.respondent_email}."))
        except Exception:
            logger.exception("Failed to send final reg email to %s", sub.respondent_email)
            messages.error(request, _("Failed to send email. Please try again."))

        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


class PreRegRejectSubmissionView(AdministratorMixin, TournamentMixin, View):
    """POST: mark a submission as rejected."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        sub = get_object_or_404(PreRegSubmission, pk=kwargs['sub_pk'], form__tournament=t)
        sub.status = SubmissionStatus.REJECTED
        sub.save(update_fields=['status'])
        messages.success(request, _(f"{sub.respondent_name or 'Submission'} marked as not selected."))
        return redirect('prereg-admin-dashboard', tournament_slug=t.slug)


# ==============================================================================
# Admin views — Independent Adjudicator
# ==============================================================================

class PreRegAdjAdminView(AdministratorMixin, TournamentMixin, TemplateView):
    """Admin view for independent adjudicator responses."""
    template_name = 'prereg/admin/adj_responses.html'
    view_permission = True

    def get(self, request, *args, **kwargs):
        t = self.tournament
        adj_form = _get_or_create_form(t, FormType.ADJ_INDEPENDENT, f"{t.short_name} — Independent Adjudicator Registration")
        fields = list(adj_form.fields.all())
        raw_submissions = list(adj_form.submissions.order_by('-submitted_at'))

        # Pre-process: attach an ordered list of (label, value) pairs to each submission
        submissions_with_data = []
        for sub in raw_submissions:
            row = []
            for field in fields:
                val = sub.data.get(str(field.pk), '')
                if isinstance(val, list):
                    val = ', '.join(val)
                row.append((field.label, val))
            submissions_with_data.append((sub, row))

        return self.render_to_response(self.get_context_data(
            adj_form=adj_form,
            form_fields=fields,
            submissions=raw_submissions,
            submissions_with_data=submissions_with_data,
            field_type_choices=FieldType.choices,
        ))


class PreRegAdjFormSettingsView(AdministratorMixin, TournamentMixin, View):
    """POST: update adj form settings."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        adj_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.ADJ_INDEPENDENT)
        adj_form.title = request.POST.get('title', adj_form.title).strip()
        adj_form.description = request.POST.get('description', '').strip()
        adj_form.is_open = 'is_open' in request.POST
        adj_form.save()
        messages.success(request, _("Adjudicator form settings saved."))
        return redirect('prereg-admin-adj', tournament_slug=t.slug)


class PreRegAdjAddFieldView(AdministratorMixin, TournamentMixin, View):
    """POST: add a field to the adj form."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        adj_form = get_object_or_404(PreRegForm, tournament=t, form_type=FormType.ADJ_INDEPENDENT)
        label = request.POST.get('label', '').strip()
        if not label:
            messages.error(request, _("Field label is required."))
            return redirect('prereg-admin-adj', tournament_slug=t.slug)

        field_type = request.POST.get('field_type', FieldType.TEXT)
        if field_type not in dict(FieldType.choices):
            field_type = FieldType.TEXT

        from django.db.models import Max
        max_order = adj_form.fields.aggregate(m=Max('order'))['m'] or 0
        PreRegFormField.objects.create(
            form=adj_form,
            label=label,
            field_type=field_type,
            required='required' in request.POST,
            options_text=request.POST.get('options_text', '').strip(),
            placeholder=request.POST.get('placeholder', '').strip(),
            is_email_field='is_email_field' in request.POST,
            is_name_field='is_name_field' in request.POST,
            order=max_order + 1,
        )
        messages.success(request, _("Field added."))
        return redirect('prereg-admin-adj', tournament_slug=t.slug)


class PreRegAdjDeleteFieldView(AdministratorMixin, TournamentMixin, View):
    """POST: delete a field from the adj form."""
    view_permission = True

    def post(self, request, *args, **kwargs):
        t = self.tournament
        field = get_object_or_404(
            PreRegFormField,
            pk=kwargs['field_pk'],
            form__tournament=t,
            form__form_type=FormType.ADJ_INDEPENDENT,
        )
        field.delete()
        messages.success(request, _("Field deleted."))
        return redirect('prereg-admin-adj', tournament_slug=t.slug)


# ==============================================================================
# Email body builders
# ==============================================================================

def _build_offer_email_body(sub, slot, prereg_form, tournament):
    lines = [
        f"Dear {sub.respondent_name or 'Team Representative'},",
        "",
        f"Congratulations! Your pre-registration for {tournament.name} has been reviewed.",
        f"You have been allocated {slot.slots_granted} slot(s).",
        "",
    ]
    if prereg_form.payment_instructions:
        lines += [
            "To confirm your slot(s), please complete payment using the details below:",
            "",
            prereg_form.payment_instructions,
            "",
        ]
    lines += [
        "Once we confirm your payment, you will receive a separate email with the final registration link.",
        "",
        "If you have any questions, please reply to this email.",
        "",
        f"Best regards,",
        f"The {tournament.short_name} Organising Committee",
    ]
    return "\n".join(lines)


def _build_final_reg_email_body(sub, final_url, tournament):
    lines = [
        f"Dear {sub.respondent_name or 'Team Representative'},",
        "",
        f"Your payment for {tournament.name} has been confirmed. Thank you!",
        "",
        "Please complete your final participant registration using the link below:",
        "",
        final_url,
        "",
        "This link is for the official registration of your team members/speakers.",
        "Please complete it as soon as possible.",
        "",
        "If you have any questions, please reply to this email.",
        "",
        f"Best regards,",
        f"The {tournament.short_name} Organising Committee",
    ]
    return "\n".join(lines)
