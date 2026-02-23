from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token generator for email verification links.

    Includes ``is_active`` in the hash so the token is invalidated the
    moment the user activates their account.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"


email_verification_token = EmailVerificationTokenGenerator()
