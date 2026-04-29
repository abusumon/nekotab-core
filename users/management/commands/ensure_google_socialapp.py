"""Ensure django-allauth Google SocialApp exists and is linked to SITE_ID.

This command is safe to run repeatedly during deploys.
"""

import os
from urllib.parse import urlparse

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create/update the Google SocialApp and link it to the configured SITE_ID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            default="",
            help="Google OAuth client ID (overrides environment variables).",
        )
        parser.add_argument(
            "--secret",
            default="",
            help="Google OAuth client secret (overrides environment variables).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        site_id = getattr(settings, "SITE_ID", 1)
        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist as exc:
            raise CommandError(f"Site with id={site_id} does not exist.") from exc

        client_id = (
            options["client_id"]
            or os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
            or os.environ.get("GOOGLE_CLIENT_ID")
            or ""
        )
        secret = (
            options["secret"]
            or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
            or os.environ.get("GOOGLE_CLIENT_SECRET")
            or ""
        )

        callback_uri = self._expected_callback_uri(site)
        self.stdout.write(f"Expected Google redirect URI: {callback_uri}")

        if not client_id or not secret:
            self.stdout.write(self.style.WARNING(
                "Google OAuth credentials are missing; skipping SocialApp sync. "
                "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET."
            ))
            return

        existing_apps = SocialApp.objects.filter(provider="google").order_by("id")
        app = existing_apps.first()
        duplicates = existing_apps[1:]

        created = False
        updated = False
        linked = False

        with transaction.atomic():
            if app is None:
                created = True
                if not dry_run:
                    app = SocialApp.objects.create(
                        provider="google",
                        name="Google OAuth",
                        client_id=client_id,
                        secret=secret,
                        key="",
                    )
            else:
                fields_to_update = []
                if app.client_id != client_id:
                    app.client_id = client_id
                    fields_to_update.append("client_id")
                if app.secret != secret:
                    app.secret = secret
                    fields_to_update.append("secret")
                if app.key:
                    app.key = ""
                    fields_to_update.append("key")

                if fields_to_update:
                    updated = True
                    if not dry_run:
                        app.save(update_fields=fields_to_update)

            if app is not None and not app.sites.filter(id=site.id).exists():
                linked = True
                if not dry_run:
                    app.sites.add(site)

            if duplicates.exists():
                duplicate_ids = ", ".join(str(a.id) for a in duplicates)
                self.stdout.write(self.style.WARNING(
                    f"Multiple Google SocialApp rows found. Keeping id={app.id}; extras: {duplicate_ids}."
                ))

        if created:
            self.stdout.write(self.style.SUCCESS("Created Google SocialApp."))
        elif updated:
            self.stdout.write(self.style.SUCCESS("Updated Google SocialApp credentials."))
        else:
            self.stdout.write("Google SocialApp credentials are already up to date.")

        if linked:
            self.stdout.write(self.style.SUCCESS(f"Linked Google SocialApp to Site id={site.id}."))
        else:
            self.stdout.write(f"Google SocialApp already linked to Site id={site.id}.")

    def _expected_callback_uri(self, site):
        base_url = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")

        if not base_url:
            scheme = "https" if not settings.DEBUG else "http"
            base_url = f"{scheme}://{site.domain}"
        else:
            parsed = urlparse(base_url)
            if parsed.scheme and parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"

        return f"{base_url}/accounts/google/login/callback/"
