"""Tests for the forum app — models, views, and API endpoints."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import ForumThread, ForumPost, ForumTag, ForumVote, ForumBookmark, ForumReport

User = get_user_model()


class ForumModelTests(TestCase):
    """Test forum model properties and constraints."""

    def setUp(self):
        self.user = User.objects.create_user(username="debater", email="debater@example.com", password="testpass123")
        self.tag = ForumTag.objects.create(name="Strategy", slug="strategy")
        self.thread = ForumThread.objects.create(
            title="Best BP strategies",
            slug="best-bp-strategies",
            author=self.user,
        )
        self.post = ForumPost.objects.create(
            thread=self.thread,
            author=self.user,
            post_type=ForumPost.PostType.OPENING,
            content="Opening argument text.",
        )

    def test_thread_str(self):
        self.assertEqual(str(self.thread), "Best BP strategies")

    def test_reply_count(self):
        self.assertEqual(self.thread.reply_count, 1)
        ForumPost.objects.create(
            thread=self.thread, author=self.user,
            post_type=ForumPost.PostType.SUPPORT, content="I agree.",
        )
        self.assertEqual(self.thread.reply_count, 2)

    def test_last_activity_uses_annotation(self):
        """When _last_activity is set via annotation, the property should use it."""
        from django.utils import timezone
        fake_time = timezone.now()
        self.thread._last_activity = fake_time
        self.assertEqual(self.thread.last_activity, fake_time)

    def test_last_activity_fallback(self):
        """When no annotation, falls back to querying posts."""
        self.assertEqual(self.thread.last_activity, self.post.created_at)

    def test_vote_score_prefetch(self):
        """vote_score should work with prefetched votes."""
        ForumVote.objects.create(user=self.user, post=self.post, vote_type=ForumVote.VoteType.UPVOTE)
        user2 = User.objects.create_user(username="user2", password="testpass123")
        ForumVote.objects.create(user=user2, post=self.post, vote_type=ForumVote.VoteType.DOWNVOTE)
        # Refresh to use prefetch
        post = ForumPost.objects.prefetch_related('votes').get(pk=self.post.pk)
        self.assertEqual(post.vote_score, 0)  # 1 up - 1 down = 0

    def test_post_depth(self):
        reply = ForumPost.objects.create(
            thread=self.thread, author=self.user, parent=self.post,
            post_type=ForumPost.PostType.COUNTERARGUMENT, content="Counter.",
        )
        self.assertEqual(self.post.depth, 0)
        self.assertEqual(reply.depth, 1)

    def test_unique_report_constraint(self):
        """A user cannot report the same post twice."""
        ForumReport.objects.create(
            reporter=self.user, post=self.post,
            reason=ForumReport.ReportReason.SPAM,
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ForumReport.objects.create(
                reporter=self.user, post=self.post,
                reason=ForumReport.ReportReason.HARASSMENT,
            )

    def test_cascade_author_set_null(self):
        """Deleting a user should set thread/post author to NULL, not cascade-delete content."""
        thread_pk = self.thread.pk
        post_pk = self.post.pk
        self.user.delete()
        self.assertTrue(ForumThread.objects.filter(pk=thread_pk).exists())
        self.assertTrue(ForumPost.objects.filter(pk=post_pk).exists())
        thread = ForumThread.objects.get(pk=thread_pk)
        self.assertIsNone(thread.author)


class ForumAPITests(TestCase):
    """Test forum REST API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="apiuser", email="api@example.com", password="testpass123")
        self.thread = ForumThread.objects.create(
            title="API Test Thread", slug="api-test-thread", author=self.user,
        )
        ForumPost.objects.create(
            thread=self.thread, author=self.user,
            post_type=ForumPost.PostType.OPENING, content="Test post.",
        )

    def test_thread_list_anonymous(self):
        response = self.client.get("/api/forum/threads/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_thread_detail(self):
        response = self.client.get(f"/api/forum/threads/{self.thread.slug}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("posts", response.data)

    def test_create_thread_requires_auth(self):
        response = self.client.post("/api/forum/threads/", {
            "title": "Unauthorized",
            "initial_post": "Should fail",
        })
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_thread_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/forum/threads/", {
            "title": "New Discussion",
            "initial_post": "Here's my argument.",
            "debate_format": "bp",
            "topic_category": "strategy",
            "skill_level": "all",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ForumThread.objects.filter(title="New Discussion").exists())

    def test_vote_toggle(self):
        self.client.force_authenticate(user=self.user)
        post = self.thread.posts.first()
        response = self.client.post("/api/forum/votes/", {"post": post.pk, "vote_type": "up"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bookmark_create_and_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/forum/bookmarks/", {"thread": self.thread.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.delete(f"/api/forum/bookmarks/{self.thread.pk}/delete/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_tag_list(self):
        ForumTag.objects.create(name="Theory", slug="theory")
        response = self.client.get("/api/forum/tags/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
