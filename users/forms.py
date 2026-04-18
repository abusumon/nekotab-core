from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm, UsernameField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Membership


class SuperuserCreationForm(UserCreationForm):
    """A form that creates a superuser from the given username and password."""

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")
        labels = {"email": _("Email address")}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user


class InviteUserForm(PasswordResetForm):
    def __init__(self, tournament, *args, **kwargs):
        self.tournament = tournament
        super().__init__(*args, **kwargs)

        self.fields['role'] = forms.ModelChoiceField(queryset=tournament.group_set.all())

    def get_users(self, email):
        user, created = get_user_model().objects.get_or_create(
            email=email,
            defaults={
                'username': email.split("@")[0],
            },
        )
        Membership.objects.get_or_create(
            user=user,
            group=self.cleaned_data['role'],
        )

        return [user]

    def save(self, *args, **kwargs):
        kwargs['extra_email_context'] = {**(kwargs['extra_email_context'] or {}), 'tournament': self.tournament}
        return super().save(*args, **kwargs)


class AcceptInvitationForm(SetPasswordForm):
    username = UsernameField(label=_("Username"), help_text=get_user_model()._meta.get_field('username').help_text)

    field_order = ('username', 'new_password1', 'new_password2')

    def save(self, commit=True):
        self.user.username = self.cleaned_data['username']
        return super().save(commit=commit)


class PublicSignupForm(UserCreationForm):
    """A form for public user registration.

    Creates the user with ``is_active=False`` so they must verify their
    email address before they can log in.
    """

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email", "password1", "password2")
        labels = {"email": _("Email address")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data['email']
        existing = get_user_model().objects.filter(email__iexact=email).first()
        if existing:
            if existing.is_active:
                raise forms.ValidationError(_("An account with this email address already exists."))
            else:
                # Delete the old unverified account so a fresh one can be created
                existing.delete()
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False  # require email verification
        if commit:
            user.save()
        return user


class PublicPasswordResetForm(PasswordResetForm):
    """Allow password reset emails to be sent to users with unusable passwords.

    Django's default PasswordResetForm.get_users() silently skips users who
    have no usable password (e.g. set_unusable_password was called).  This is
    exactly the situation for users whose passwords were wiped by allauth's
    email-authentication security measure.  For those users, Forgot Password
    is the *only* way to regain access, so we must send the email.
    """

    def get_users(self, email):
        User = get_user_model()
        return User._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )


class PublicLoginForm(AuthenticationForm):
    """Allow username-or-email login and clearer inactive account feedback."""

    username = UsernameField(label=_("Username or email"))
    error_messages = {
        **AuthenticationForm.error_messages,
        'inactive': _("This account isn't activated yet. Please verify your email first."),
    }

    def clean(self):
        username_input = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username_input or not password:
            return self.cleaned_data

        user_model = get_user_model()
        candidate_qs = user_model._default_manager.filter(username__iexact=username_input).order_by('id')
        auth_username = username_input

        if '@' in username_input:
            email_qs = user_model._default_manager.filter(email__iexact=username_input).order_by('id')
            email_match = email_qs.first()
            if email_match is not None:
                auth_username = email_match.get_username()
                candidate_qs = email_qs

        self.user_cache = authenticate(self.request, username=auth_username, password=password)

        if self.user_cache is None:
            for candidate in candidate_qs.filter(is_active=False):
                if candidate.check_password(password):
                    raise ValidationError(self.error_messages['inactive'], code='inactive')
            raise self.get_invalid_login_error()

        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
