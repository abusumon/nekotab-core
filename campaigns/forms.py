from django import forms
from django.utils.translation import gettext_lazy as _
from .models import EmailCampaign
from participant_crm.models import CampaignAudience, ParticipantProfile, ParticipantTag
from tournaments.models import Tournament


class EmailCampaignForm(forms.ModelForm):
    """Form for creating and editing email campaigns."""
    
    class Meta:
        model = EmailCampaign
        fields = ['name', 'subject', 'preview_text', 'html_content', 'plain_text_content', 'send_to_all']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., February Newsletter'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 🎉 Exciting News from NekoTab!'
            }),
            'preview_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Preview text shown in inbox...'
            }),
            'html_content': forms.Textarea(attrs={
                'class': 'form-control html-editor',
                'rows': 20
            }),
            'plain_text_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Plain text version (optional - auto-generated if empty)'
            }),
            'send_to_all': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


ROLE_CHOICES = [
    ('debater', 'Debaters'),
    ('adjudicator', 'Adjudicators'),
    ('tab_director', 'Tab Directors'),
    ('hybrid', 'Hybrid'),
]


class CampaignAudienceForm(forms.Form):
    """Form for configuring target audience segment on a campaign."""

    use_audience = forms.BooleanField(
        required=False, initial=False,
        label=_("Target specific audience segment"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_use_audience'}),
    )
    roles = forms.MultipleChoiceField(
        required=False, choices=ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'audience-checkbox'}),
    )
    tournament_filter = forms.ModelChoiceField(
        required=False, queryset=Tournament.objects.order_by('-created_at'),
        empty_label='All tournaments',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    tag_filter = forms.ModelMultipleChoiceField(
        required=False, queryset=ParticipantTag.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'audience-checkbox'}),
    )
    active_since = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    custom_emails = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'one@example.com\ntwo@example.com',
        }),
    )

    def save_audience(self, campaign):
        """Create or update CampaignAudience for the given campaign."""
        if not self.cleaned_data.get('use_audience'):
            # Remove existing audience if toggled off
            CampaignAudience.objects.filter(campaign=campaign).delete()
            return None

        audience, _ = CampaignAudience.objects.get_or_create(campaign=campaign)
        audience.roles = self.cleaned_data.get('roles', [])
        audience.tournament_filter = self.cleaned_data.get('tournament_filter')
        audience.active_since = self.cleaned_data.get('active_since')
        audience.custom_emails = self.cleaned_data.get('custom_emails', '')
        audience.save()
        # M2M must be set after save
        tags = self.cleaned_data.get('tag_filter', [])
        audience.tag_filter.set(tags)
        return audience

    @classmethod
    def from_campaign(cls, campaign):
        """Pre-populate form from an existing CampaignAudience."""
        try:
            aud = campaign.audience
        except CampaignAudience.DoesNotExist:
            return cls()
        return cls(initial={
            'use_audience': True,
            'roles': aud.roles or [],
            'tournament_filter': aud.tournament_filter_id,
            'tag_filter': aud.tag_filter.all(),
            'active_since': aud.active_since,
            'custom_emails': aud.custom_emails,
        })


class TestEmailForm(forms.Form):
    """Form to send a test email before campaign launch."""
    
    test_email = forms.EmailField(
        label=_("Test Email Address"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
