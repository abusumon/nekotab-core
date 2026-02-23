"""Management command to handle GDPR data subject requests.

Usage:
    # Export all data for a user (GDPR Article 15 — Right of Access)
    python manage.py gdpr_user_data export --username alice --output /tmp/alice_data.json

    # Anonymize a user (GDPR Article 17 — Right to Erasure)
    python manage.py gdpr_user_data anonymize --username alice

    # Anonymize with dry-run first
    python manage.py gdpr_user_data anonymize --username alice --dry-run

    # Delete account entirely (cascades all related data)
    python manage.py gdpr_user_data delete --username alice --confirm
"""

import json
import logging
import uuid
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "GDPR data subject operations: export, anonymize, or delete user data."

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["export", "anonymize", "delete"],
            help="Action to perform: export (Article 15), anonymize (Article 17), or delete.",
        )
        parser.add_argument("--username", required=True, help="Username of the data subject.")
        parser.add_argument("--email", default=None, help="Email as secondary identifier.")
        parser.add_argument("--output", default=None, help="Output file path for export action.")
        parser.add_argument("--dry-run", action="store_true", help="Preview what would happen without making changes.")
        parser.add_argument("--confirm", action="store_true", help="Required for delete action.")

    def handle(self, *args, **options):
        action = options["action"]
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found.")

        if options["email"] and user.email != options["email"]:
            raise CommandError(f"Email mismatch: user email is '{user.email}', provided '{options['email']}'.")

        if action == "export":
            self._export(user, options)
        elif action == "anonymize":
            self._anonymize(user, options)
        elif action == "delete":
            self._delete(user, options)

    def _export(self, user, options):
        """Export all PII and related data for a user (GDPR Article 15)."""
        data = {
            "export_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "username": user.username,
                "gdpr_article": "Article 15 — Right of Access",
            },
            "account": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "is_active": user.is_active,
            },
            "forum_posts": [],
            "forum_threads": [],
            "forum_votes": [],
            "forum_bookmarks": [],
            "forum_reports": [],
            "page_views": [],
            "tournament_participation": [],
            "feedback_given": [],
            "badges": [],
        }

        # Forum data
        try:
            from forum.models import ForumPost, ForumThread, ForumVote, ForumBookmark, ForumReport
            data["forum_threads"] = list(
                ForumThread.objects.filter(author=user).values(
                    "id", "title", "slug", "created_at", "debate_format", "topic_category"
                )
            )
            data["forum_posts"] = list(
                ForumPost.objects.filter(author=user).values(
                    "id", "thread_id", "post_type", "content", "created_at", "is_edited"
                )
            )
            data["forum_votes"] = list(
                ForumVote.objects.filter(user=user).values("id", "post_id", "vote_type", "created_at")
            )
            data["forum_bookmarks"] = list(
                ForumBookmark.objects.filter(user=user).values("id", "thread_id", "created_at")
            )
            data["forum_reports"] = list(
                ForumReport.objects.filter(reporter=user).values("id", "post_id", "reason", "details", "created_at")
            )
        except Exception:
            pass

        # Analytics / page views
        try:
            from analytics.models import PageView
            data["page_views"] = list(
                PageView.objects.filter(user=user).values(
                    "path", "full_url", "timestamp", "device_type", "browser", "os", "country", "city"
                )[:1000]  # Limit to last 1000 to keep file manageable
            )
        except Exception:
            pass

        # Tournament participation (speakers, adjudicators)
        try:
            from participants.models import Person
            persons = Person.objects.filter(email=user.email)
            for person in persons:
                entry = {
                    "person_id": person.pk,
                    "name": person.name,
                    "email": person.email,
                }
                # Check if speaker
                if hasattr(person, 'speaker'):
                    entry["role"] = "speaker"
                    entry["team"] = str(person.speaker.team) if person.speaker.team else None
                elif hasattr(person, 'adjudicator'):
                    entry["role"] = "adjudicator"
                    entry["tournament"] = str(person.adjudicator.tournament) if person.adjudicator.tournament else None
                data["tournament_participation"].append(entry)
        except Exception:
            pass

        # Feedback
        try:
            from adjfeedback.models import AdjudicatorFeedback
            data["feedback_given"] = list(
                AdjudicatorFeedback.objects.filter(submitter=user).values(
                    "id", "adjudicator_id", "confirmed", "timestamp", "score"
                )
            )
        except Exception:
            pass

        # Badges
        try:
            from forum.models import UserBadge
            data["badges"] = list(
                UserBadge.objects.filter(user=user).values(
                    "badge_type", "verified", "awarded_at"
                )
            )
        except Exception:
            pass

        output = options.get("output") or f"gdpr_export_{user.username}_{datetime.utcnow().strftime('%Y%m%d')}.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"Exported data for '{user.username}' → {output}"))
        logger.info("GDPR export completed for user %s → %s", user.username, output)

    def _anonymize(self, user, options):
        """Anonymize user PII while preserving structural data (GDPR Article 17)."""
        dry_run = options["dry_run"]
        anon_id = uuid.uuid4().hex[:8]
        anon_username = f"deleted_user_{anon_id}"
        anon_email = f"{anon_id}@anonymized.invalid"

        self.stdout.write(f"Anonymizing user '{user.username}' (id={user.pk})")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — no changes will be made"))

        changes = []

        # 1. User account
        changes.append(f"  username: '{user.username}' → '{anon_username}'")
        changes.append(f"  email: '{user.email}' → '{anon_email}'")
        changes.append(f"  first_name: '{user.first_name}' → ''")
        changes.append(f"  last_name: '{user.last_name}' → ''")
        changes.append("  password: set unusable")
        changes.append("  is_active: False")

        if not dry_run:
            user.username = anon_username
            user.email = anon_email
            user.first_name = ""
            user.last_name = ""
            user.set_unusable_password()
            user.is_active = False
            user.save()

        # 2. Person records (participants)
        try:
            from participants.models import Person
            persons = Person.objects.filter(email=user.email)
            count = persons.count()
            if count:
                changes.append(f"  participants.Person: {count} record(s) → anonymous=True, email cleared")
                if not dry_run:
                    persons.update(
                        anonymous=True,
                        email="",
                        phone="",
                        name=f"Anonymized Participant {anon_id}",
                    )
        except Exception:
            pass

        # 3. Page views
        try:
            from analytics.models import PageView
            pv_count = PageView.objects.filter(user=user).count()
            if pv_count:
                changes.append(f"  analytics.PageView: {pv_count} record(s) → user=NULL, ip cleared")
                if not dry_run:
                    PageView.objects.filter(user=user).update(user=None, ip_address=None, user_agent="")
        except Exception:
            pass

        # 4. Active sessions
        try:
            from analytics.models import ActiveSession
            session_count = ActiveSession.objects.filter(user=user).count()
            if session_count:
                changes.append(f"  analytics.ActiveSession: {session_count} record(s) deleted")
                if not dry_run:
                    ActiveSession.objects.filter(user=user).delete()
        except Exception:
            pass

        for line in changes:
            self.stdout.write(line)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete — re-run without --dry-run to apply."))
        else:
            self.stdout.write(self.style.SUCCESS(f"User '{anon_username}' anonymized successfully."))
            logger.info("GDPR anonymization completed for user pk=%d (now %s)", user.pk, anon_username)

    def _delete(self, user, options):
        """Permanently delete a user account and all related data."""
        if not options["confirm"]:
            raise CommandError("Account deletion requires --confirm flag. This action is irreversible!")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: Would delete user '{user.username}' (id={user.pk}) and all related data."
            ))
            return

        username = user.username
        user_pk = user.pk
        user.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted user '{username}' (id={user_pk}) and all cascade-related data."))
        logger.info("GDPR deletion completed for user pk=%d (was %s)", user_pk, username)
