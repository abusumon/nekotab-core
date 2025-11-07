from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail, get_connection
from django.conf import settings

class Command(BaseCommand):
    help = "Send a test email to verify SMTP configuration. Usage: manage.py sendtestemail you@example.com"

    def add_arguments(self, parser):
        parser.add_argument('recipient', nargs=1, help='Email address to send the test message to')

    def handle(self, *args, **options):
        recipient = options['recipient'][0]
        subject = 'Tabbycat Email Configuration Test'
        body = (
            'This is a test email from Tabbycat to confirm that the SMTP backend is working.\n\n'
            f'DEFAULT_FROM_EMAIL={getattr(settings, "DEFAULT_FROM_EMAIL", "(unset)")}\n'
            f'EMAIL_BACKEND={getattr(settings, "EMAIL_BACKEND", "(unset)")}\n'
            f'EMAIL_HOST={getattr(settings, "EMAIL_HOST", "(unset)")}\n'
            f'EMAIL_PORT={getattr(settings, "EMAIL_PORT", "(unset)")}\n'
            f'EMAIL_USE_TLS={getattr(settings, "EMAIL_USE_TLS", "(unset)")}\n'
        )
        try:
            # Force use of configured backend; will raise if misconfigured
            connection = get_connection()
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], connection=connection)
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient}. Check their inbox."))
        except Exception as e:
            raise CommandError(f"Failed to send test email: {e}")
