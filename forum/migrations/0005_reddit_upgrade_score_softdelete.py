"""Add score, is_deleted, comment_count fields and indexes for Reddit-like forum."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0004_add_missing_indexes'),
    ]

    operations = [
        # --- ForumThread additions ---
        migrations.AddField(
            model_name='forumthread',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, verbose_name='soft-deleted'),
        ),
        migrations.AddField(
            model_name='forumthread',
            name='score',
            field=models.IntegerField(
                db_index=True, default=0,
                help_text='Cached net score of the opening post (updated on vote)',
                verbose_name='score',
            ),
        ),
        migrations.AddField(
            model_name='forumthread',
            name='comment_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Cached count of non-deleted posts (updated on post create/delete)',
                verbose_name='comment count',
            ),
        ),
        migrations.AddIndex(
            model_name='forumthread',
            index=models.Index(fields=['-score', '-created_at'], name='forum_forum_score_d_idx'),
        ),

        # --- ForumPost additions ---
        migrations.AddField(
            model_name='forumpost',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, verbose_name='soft-deleted'),
        ),
        migrations.AddField(
            model_name='forumpost',
            name='score',
            field=models.IntegerField(
                db_index=True, default=0,
                help_text='Net vote score (upvotes − downvotes), updated on vote',
                verbose_name='cached score',
            ),
        ),
        migrations.AddIndex(
            model_name='forumpost',
            index=models.Index(fields=['thread', '-score'], name='forum_forum_thread__score_idx'),
        ),
    ]
