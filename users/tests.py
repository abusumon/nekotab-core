"""Tests for the users app — signup, email verification, and GDPR commands."""

from unittest.mock import patch

from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core import mail
from django.http import HttpResponseRedirect
from django.test import TestCase, override_settings
from django.urls import reverse

from .tokens import email_verification_token

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PublicSignupTests(TestCase):
    """Test the public signup flow with email verification."""

    def test_signup_creates_inactive_user(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Str0ngP@ssw0rd!',
            'password2': 'Str0ngP@ssw0rd!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        self.assertFalse(user.is_active)

    def test_signup_sends_verification_email(self):
        self.client.post(reverse('signup'), {
            'username': 'emailtest',
            'email': 'emailtest@example.com',
            'password1': 'Str0ngP@ssw0rd!',
            'password2': 'Str0ngP@ssw0rd!',
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verify', mail.outbox[0].body.lower())

    def test_duplicate_active_email_rejected(self):
        User.objects.create_user(username='existing', email='taken@example.com', password='test123', is_active=True)
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'taken@example.com',
            'password1': 'Str0ngP@ssw0rd!',
            'password2': 'Str0ngP@ssw0rd!',
        })
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_verification_link_activates_user(self):
        self.client.post(reverse('signup'), {
            'username': 'verifytest',
            'email': 'verifytest@example.com',
            'password1': 'Str0ngP@ssw0rd!',
            'password2': 'Str0ngP@ssw0rd!',
        })
        user = User.objects.get(username='verifytest')
        self.assertFalse(user.is_active)

        # Generate the same token the view generates
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        response = self.client.get(reverse('activate-account', args=[uid, token]))
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_invalid_token_rejected(self):
        user = User.objects.create_user(username='badtoken', password='test123', is_active=False)
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(reverse('activate-account', args=[uid, 'invalid-token']))
        # Should redirect with error message, user stays inactive
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_authenticated_user_redirected_from_signup(self):
        user = User.objects.create_user(username='authed', password='test123', is_active=True)
        self.client.login(username='authed', password='test123')
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 302)


class TokenGeneratorTests(TestCase):
    """Test the email verification token generator."""

    def test_token_valid_for_inactive_user(self):
        user = User.objects.create_user(username='tokentest', password='test', is_active=False)
        token = email_verification_token.make_token(user)
        self.assertTrue(email_verification_token.check_token(user, token))

    def test_token_invalidated_after_activation(self):
        user = User.objects.create_user(username='tokentest2', password='test', is_active=False)
        token = email_verification_token.make_token(user)
        user.is_active = True
        user.save()
        self.assertFalse(email_verification_token.check_token(user, token))


class LoginBehaviorTests(TestCase):
    """Test login behavior for inactive accounts and email-based login."""

    def test_inactive_user_shows_activation_message(self):
        User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='Str0ngP@ssw0rd!',
            is_active=False,
        )
        response = self.client.post(reverse('login'), {
            'username': 'inactiveuser',
            'password': 'Str0ngP@ssw0rd!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "isn't activated yet")

    def test_active_user_can_log_in_with_email(self):
        User.objects.create_user(
            username='emailuser',
            email='emailuser@example.com',
            password='Str0ngP@ssw0rd!',
            is_active=True,
        )
        response = self.client.post(reverse('login'), {
            'username': 'emailuser@example.com',
            'password': 'Str0ngP@ssw0rd!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


@override_settings(SOCIALACCOUNT_PROVIDERS={'google': {}})
class GoogleOAuthGuardTests(TestCase):

    def test_unconfigured_google_shows_visible_error(self):
        response = self.client.get(reverse('google-login-guard'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google sign-in isn't configured yet")

    @patch('users.views.oauth2_login')
    def test_socialapp_without_site_gets_linked_and_dispatched(self, oauth2_login_mock):
        oauth2_login_mock.return_value = HttpResponseRedirect('/oauth-started/')

        app = SocialApp.objects.create(
            provider='google',
            name='Google OAuth',
            client_id='cid',
            secret='sec',
            key='',
        )
        site = Site.objects.get(id=1)
        self.assertFalse(app.sites.filter(id=site.id).exists())

        response = self.client.get(reverse('google-login-guard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/oauth-started/')

        app.refresh_from_db()
        self.assertTrue(app.sites.filter(id=site.id).exists())
        oauth2_login_mock.assert_called_once()


@override_settings(SOCIALACCOUNT_PROVIDERS={
    'google': {
        'APP': {
            'client_id': 'settings-client-id',
            'secret': 'settings-secret',
            'key': '',
        }
    }
})
class EnsureGoogleSocialAppCommandTests(TestCase):

    def test_removes_db_google_app_when_settings_app_exists(self):
        app = SocialApp.objects.create(
            provider='google',
            name='Google OAuth',
            client_id='db-client-id',
            secret='db-secret',
            key='',
        )
        app.sites.add(Site.objects.get(id=1))

        call_command('ensure_google_socialapp')

        self.assertFalse(SocialApp.objects.filter(provider='google').exists())
