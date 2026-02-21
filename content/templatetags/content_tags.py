from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from content.models import Article

register = template.Library()


@register.simple_tag
def related_articles_for_format(format_slug, limit=3):
    """Return published articles related to a debate format.
    Usage: {% related_articles_for_format "bp" 3 as articles %}
    """
    return (
        Article.objects
        .filter(status=Article.Status.PUBLISHED, related_format_slugs__contains=[format_slug])
        [:limit]
    )


@register.inclusion_tag('content/includes/related_articles_card.html')
def show_related_articles(format_slug, limit=3):
    """Render a card with links to related learn articles.
    Usage: {% show_related_articles "bp" %}
    """
    articles = (
        Article.objects
        .filter(status=Article.Status.PUBLISHED, related_format_slugs__contains=[format_slug])
        [:limit]
    )
    return {'articles': articles, 'format_slug': format_slug}


@register.simple_tag
def tournament_context_text(tournament, content_block=None):
    """Generate deterministic contextual text from tournament metadata.
    This is NOT AI-generated fluff — it's a structured template.
    """
    name = escape(tournament.name)
    short = escape(tournament.short_name) if tournament.short_name else name

    parts = [f"{name} is a competitive debate tournament"]

    if content_block:
        if content_block.format_description:
            parts[0] += f" using the {escape(content_block.format_description)} format"
        if content_block.host_organization:
            parts.append(f"Hosted by {escape(content_block.host_organization)}")
        if content_block.location:
            parts.append(f"held in {escape(content_block.location)}")
        if content_block.start_date and content_block.end_date:
            parts.append(
                f"running from {content_block.start_date.strftime('%B %d, %Y')} "
                f"to {content_block.end_date.strftime('%B %d, %Y')}"
            )
        elif content_block.start_date:
            parts.append(f"on {content_block.start_date.strftime('%B %d, %Y')}")

    # Add stats
    try:
        team_count = tournament.team_set.count()
        round_count = tournament.round_set.count()
        adj_count = tournament.adjudicator_set.count()
        stats = []
        if team_count:
            stats.append(f"{team_count} teams")
        if round_count:
            stats.append(f"{round_count} rounds")
        if adj_count:
            stats.append(f"{adj_count} adjudicators")
        if stats:
            parts.append(f"The tournament features {', '.join(stats)}")
    except Exception:
        pass

    parts.append(
        f"View the full results, speaker standings, and round-by-round draws for {short} on NekoTab, "
        "a modern debate tournament tabulation platform"
    )

    text = '. '.join(parts) + '.'
    return mark_safe(f'<p class="tournament-context-text">{text}</p>')


@register.simple_tag
def content_threshold_met(tournament):
    """Check if a tournament has enough content to be indexable.
    Content threshold conditions:
    1. Has at least 1 completed round with published results
    2. Has at least 2 teams
    3. Tournament is active and listed
    4. Has a name (not blank)

    Returns True/False.
    """
    if not tournament.active or not tournament.is_listed:
        return False
    if not tournament.name or len(tournament.name.strip()) < 3:
        return False

    try:
        team_count = tournament.team_set.count()
        if team_count < 2:
            return False
    except Exception:
        return False

    try:
        from results.models import BallotSubmission
        has_results = BallotSubmission.objects.filter(
            debate__round__tournament=tournament,
            confirmed=True
        ).exists()
        if not has_results:
            # Check if at least one round is completed
            completed_rounds = tournament.round_set.filter(
                completed=True
            ).exists()
            if not completed_rounds:
                return False
    except Exception:
        return False

    return True
