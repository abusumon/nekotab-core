from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = "Checks AdSense runtime configuration and reports common blockers"

    def handle(self, *args, **options):
        enabled = bool(getattr(settings, 'ADSENSE_ENABLED', False))
        publisher_id = str(getattr(settings, 'ADSENSE_PUBLISHER_ID', '') or '').strip()
        content_slot = str(getattr(settings, 'ADSENSE_SLOT_CONTENT', '') or '').strip()
        footer_slot = str(getattr(settings, 'ADSENSE_SLOT_FOOTER', '') or '').strip()
        table_slot = str(getattr(settings, 'ADSENSE_SLOT_TABLE', '') or '').strip()

        problems = []

        self.stdout.write(self.style.MIGRATE_HEADING("AdSense Configuration"))
        self.stdout.write(f"ADSENSE_ENABLED: {'true' if enabled else 'false'}")
        self.stdout.write(f"ADSENSE_PUBLISHER_ID: {publisher_id or '<empty>'}")
        self.stdout.write(f"ADSENSE_SLOT_CONTENT: {content_slot or '<empty>'}")
        self.stdout.write(f"ADSENSE_SLOT_FOOTER: {footer_slot or '<empty>'}")
        self.stdout.write(f"ADSENSE_SLOT_TABLE: {table_slot or '<empty>'}")

        if not enabled:
            problems.append("ADSENSE_ENABLED is false; ads are disabled globally.")

        if not publisher_id:
            problems.append("ADSENSE_PUBLISHER_ID is empty.")
        elif not publisher_id.startswith('ca-pub-'):
            problems.append("ADSENSE_PUBLISHER_ID should start with 'ca-pub-'.")

        slots = {
            'ADSENSE_SLOT_CONTENT': content_slot,
            'ADSENSE_SLOT_FOOTER': footer_slot,
            'ADSENSE_SLOT_TABLE': table_slot,
        }

        missing_slots = [name for name, value in slots.items() if not value]
        if missing_slots:
            problems.append(
                "Some ad slots are empty; explicit ad units using AUTO_* placeholders will not render for those positions: "
                + ", ".join(missing_slots)
            )

        non_numeric_slots = [name for name, value in slots.items() if value and not value.isdigit()]
        if non_numeric_slots:
            problems.append(
                "Some ad slots are non-numeric; data-ad-slot must be numeric: "
                + ", ".join(non_numeric_slots)
            )

        if problems:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Status: FAIL"))
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"- {problem}"))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Status: PASS"))
        self.stdout.write(self.style.SUCCESS("AdSense runtime configuration looks valid."))
