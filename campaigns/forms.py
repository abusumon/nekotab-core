from django import forms
from django.utils.translation import gettext_lazy as _
from .models import EmailCampaign


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


class TestEmailForm(forms.Form):
    """Form to send a test email before campaign launch."""
    
    test_email = forms.EmailField(
        label=_("Test Email Address"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
