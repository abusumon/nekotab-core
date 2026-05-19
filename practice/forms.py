from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PracticeSession, SessionRoom, SessionParticipant, SpeakerScore, DebateFormat, SessionStatus, ParticipantRole


class PracticeSessionForm(forms.ModelForm):
    class Meta:
        model = PracticeSession
        fields = ['title', 'date', 'start_time', 'format', 'venue', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Weekly Practice #12")}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'format': forms.Select(attrs={'class': 'form-control'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Room 201, Main Building")}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SessionStatusForm(forms.ModelForm):
    class Meta:
        model = PracticeSession
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class SessionRoomForm(forms.ModelForm):
    class Meta:
        model = SessionRoom
        fields = ['name', 'motion']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("e.g. Room A")}),
            'motion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Motion for this room")}),
        }


class AddParticipantForm(forms.Form):
    membership_id = forms.IntegerField(widget=forms.HiddenInput())
    role = forms.ChoiceField(
        choices=ParticipantRole.choices,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
    )


class ScoreEntryForm(forms.ModelForm):
    class Meta:
        model = SpeakerScore
        fields = ['score', 'reply_score', 'won', 'notes']
        widgets = {
            'score': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm score-input',
                'step': '0.5', 'min': '0', 'max': '100',
                'placeholder': '—',
            }),
            'reply_score': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm score-input',
                'step': '0.5', 'min': '0', 'max': '40',
                'placeholder': '—',
            }),
            'won': forms.Select(
                choices=[(None, '—'), (True, 'Win'), (False, 'Loss')],
                attrs={'class': 'form-control form-control-sm'},
            ),
            'notes': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': _("Adjudicator notes"),
            }),
        }
