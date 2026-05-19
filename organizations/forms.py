from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tournaments.models import (
    Tournament,
    TournamentMetadata,
    TournamentStaffMembership,
    normalize_slug,
    validate_dns_safe_slug,
)
from .models import Organization, OrganizationMembership


class WorkspaceTournamentCreateForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'short_name', 'slug']
        help_texts = {
            'slug': _("URL-safe identifier. Lowercase letters, numbers, and hyphens only."),
        }

    num_prelim_rounds = forms.IntegerField(
        min_value=1,
        label=_("Number of preliminary rounds"),
    )

    break_size = forms.IntegerField(
        min_value=2, required=False,
        label=_("Number of teams in the open break"),
        help_text=_("Leave blank if there are no break rounds."),
    )

    event_start_date = forms.DateField(
        required=False,
        label=_("Actual event start date"),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    event_end_date = forms.DateField(
        required=False,
        label=_("Actual event end date"),
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    registration_open = forms.DateTimeField(
        required=False,
        label=_("Registration opens"),
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    registration_close = forms.DateTimeField(
        required=False,
        label=_("Registration closes"),
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    event_format = forms.CharField(
        max_length=100,
        required=False,
        label=_("Format"),
    )
    venue = forms.CharField(
        max_length=200,
        required=False,
        label=_("Venue"),
    )
    visibility = forms.ChoiceField(
        choices=TournamentMetadata.Visibility.choices,
        required=True,
        initial=TournamentMetadata.Visibility.ORGANIZATION,
        label=_("Visibility"),
    )
    registration_type = forms.ChoiceField(
        choices=TournamentMetadata.RegistrationType.choices,
        required=True,
        initial=TournamentMetadata.RegistrationType.OPEN,
        label=_("Registration type"),
    )
    lifecycle_status = forms.ChoiceField(
        choices=TournamentMetadata.Status.choices,
        required=True,
        initial=TournamentMetadata.Status.DRAFT,
        label=_("Status"),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        # Apply workspace styling classes
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['event_format'].widget.attrs.setdefault('placeholder', _('e.g. British Parliamentary'))
        self.fields['venue'].widget.attrs.setdefault('placeholder', _('e.g. Main Hall, Dhaka University'))

    def clean_slug(self):
        raw = self.cleaned_data.get('slug', '')
        slug = normalize_slug(raw)
        if slug != raw:
            self.cleaned_data['slug'] = slug
        if Tournament.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is already taken."))
        from organizations.models import Organization
        if Organization.objects.filter(slug__iexact=slug, is_workspace_enabled=True).exists():
            raise forms.ValidationError(_("This slug is reserved by an organization."))
        return slug

    def clean(self):
        cleaned = super().clean()
        event_start_date = cleaned.get('event_start_date')
        event_end_date = cleaned.get('event_end_date')
        registration_open = cleaned.get('registration_open')
        registration_close = cleaned.get('registration_close')

        if event_start_date and event_end_date and event_end_date < event_start_date:
            self.add_error('event_end_date', _("Event end date must be on or after event start date."))

        if registration_open and registration_close and registration_close < registration_open:
            self.add_error('registration_close', _("Registration close must be after registration open."))

        return cleaned


class OrganizationRegistrationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'slug', 'description']
        help_texts = {
            'slug': _("URL-safe identifier for your workspace subdomain. Lowercase letters, numbers, and hyphens only."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_slug(self):
        slug = self.cleaned_data['slug'].lower()
        validate_dns_safe_slug(slug)
        if Organization.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is already taken."))
        if Tournament.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is reserved."))
        from core.models import SubdomainSlugReservation
        if SubdomainSlugReservation.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is already in use."))
        reserved = getattr(settings, 'RESERVED_SUBDOMAINS', [])
        if slug in reserved:
            raise forms.ValidationError(_("This slug is reserved."))
        return slug


# ---------------------------------------------------------------------------
# Member invitation form
# ---------------------------------------------------------------------------

# Roles that admins can assign (not owner — that would be a transfer)
_INVITABLE_ROLES = [
    (OrganizationMembership.Role.ADMIN,     _("Admin")),
    (OrganizationMembership.Role.TABMASTER, _("Tabmaster")),
    (OrganizationMembership.Role.EDITOR,    _("Editor")),
    (OrganizationMembership.Role.VIEWER,    _("Viewer")),
]


class InviteMemberForm(forms.Form):
    name = forms.CharField(
        max_length=200, label=_("Full name"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Jane Smith")}),
    )
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _("jane@example.com")}),
    )
    role = forms.ChoiceField(
        choices=_INVITABLE_ROLES, label=_("Role"),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(
        max_length=30, required=False, label=_("Phone (optional)"),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    department = forms.CharField(
        max_length=100, required=False, label=_("Department (optional)"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Computer Science")}),
    )
    batch = forms.CharField(
        max_length=50, required=False, label=_("Batch / Session (optional)"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. 2023–2024")}),
    )
    designation = forms.CharField(
        max_length=100, required=False, label=_("Designation (optional)"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Best Speaker finalist")}),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._organization = organization

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if self._organization:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user and OrganizationMembership.objects.filter(
                organization=self._organization, user=existing_user,
            ).exists():
                raise forms.ValidationError(
                    _("This email address is already a member of this organization."),
                )
            # Check for a pending (unexpired, unaccepted) invitation
            from django.utils import timezone
            from .models import OrganizationInvitation
            if OrganizationInvitation.objects.filter(
                organization=self._organization,
                email__iexact=email,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists():
                raise forms.ValidationError(
                    _("An active invitation has already been sent to this address."),
                )
        return email


class TournamentStaffInviteForm(forms.Form):
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('staff@example.com')}),
    )
    role = forms.ChoiceField(
        choices=TournamentStaffMembership.Role.choices,
        label=_("Role"),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, tournament=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._tournament = tournament

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if self._tournament:
            from django.utils import timezone
            from tournaments.models import TournamentStaffInvitation

            if TournamentStaffInvitation.objects.filter(
                tournament=self._tournament,
                email__iexact=email,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists():
                raise forms.ValidationError(_("An active invitation already exists for this email."))
        return email

