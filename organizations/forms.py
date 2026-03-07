from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from tournaments.models import Tournament, validate_dns_safe_slug
from .models import Organization


class WorkspaceTournamentCreateForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'short_name', 'slug']
        help_texts = {
            'slug': _("URL-safe identifier. Lowercase letters, numbers, and hyphens only."),
        }

    num_prelim_rounds = forms.IntegerField(
        min_value=1, max_value=50, initial=5,
        label=_("Number of preliminary rounds"),
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        # Apply workspace styling classes
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_slug(self):
        slug = self.cleaned_data['slug'].lower()
        validate_dns_safe_slug(slug)
        if Tournament.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(_("This slug is already taken."))
        from organizations.models import Organization
        if Organization.objects.filter(slug__iexact=slug, is_workspace_enabled=True).exists():
            raise forms.ValidationError(_("This slug is reserved by an organization."))
        return slug


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
