"""Seed data: categories + article stubs for /learn."""
from django.db import migrations


def seed_content(apps, schema_editor):
    Category = apps.get_model('content', 'ArticleCategory')
    Article = apps.get_model('content', 'Article')

    # --- Categories ---
    cats = {
        'formats': Category.objects.create(
            name='Debate Formats', slug='formats', icon='🏛️', order=1,
            description='Guides to parliamentary debate formats used worldwide.'
        ),
        'judging': Category.objects.create(
            name='Judging & Adjudication', slug='judging', icon='⚖️', order=2,
            description='Resources for debate adjudicators at every level.'
        ),
        'training': Category.objects.create(
            name='Speaker Training', slug='training', icon='🎤', order=3,
            description='Improve your debating skills with structured guides.'
        ),
        'hosting': Category.objects.create(
            name='Tournament Hosting', slug='hosting', icon='📋', order=4,
            description='Best practices for organising and running debate tournaments.'
        ),
    }

    # --- Article Stubs ---
    stubs = [
        # PUBLISHED stubs (indexable)
        {
            'title': 'What Is British Parliamentary (BP) Debate?',
            'slug': 'what-is-bp-debate',
            'category': cats['formats'],
            'status': 'published',
            'reading_time_minutes': 4,
            'related_format_slugs': ['bp', 'british-parliamentary'],
            'summary': 'A comprehensive introduction to British Parliamentary debate — the most widely used format in university-level competitive debating worldwide.',
            'body': (
                '<h2>Overview</h2>'
                '<p>British Parliamentary (BP) debate is a four-team format where two teams argue for the government (proposition) '
                'and two teams argue for the opposition. Each team has two speakers, making eight speakers total in each debate.</p>'
                '<h2>Structure</h2>'
                '<p>The debate is divided into an Opening Half (Opening Government and Opening Opposition) and a Closing Half '
                '(Closing Government and Closing Opposition). Closing teams must introduce an "extension" — a new substantive '
                'argument that adds to their side\'s case.</p>'
                '<p>Full guide coming soon. This page will be expanded with detailed explanations of roles, strategy, and scoring.</p>'
            ),
        },
        {
            'title': 'Understanding Australs 3v3 Format',
            'slug': 'australs-3v3-format',
            'category': cats['formats'],
            'status': 'published',
            'reading_time_minutes': 3,
            'related_format_slugs': ['australs', '3v3', 'asian-parliamentary'],
            'summary': 'Learn about the Australs (3v3) debate format — a two-team structure with three speakers per side widely used in Asia-Pacific debate circuits.',
            'body': (
                '<h2>Overview</h2>'
                '<p>The Australs format features two teams — Affirmative and Negative — with three speakers each. '
                'It is the standard format for competitions like the Australasian Intervarsity Debating Championships and '
                'many Asian Parliamentary tournaments.</p>'
                '<h2>Key Differences from BP</h2>'
                '<p>Unlike BP, there are no closing teams or extensions. The focus is on deep clash between two sides, '
                'with a reply speech from the first or second speaker summarizing the debate.</p>'
                '<p>Detailed strategy guides and scoring criteria coming soon.</p>'
            ),
        },
        {
            'title': 'WSDC Format Explained',
            'slug': 'wsdc-format-explained',
            'category': cats['formats'],
            'status': 'published',
            'reading_time_minutes': 3,
            'related_format_slugs': ['wsdc', 'world-schools'],
            'summary': 'An overview of the World Schools Debating Championship (WSDC) format — the premier format for high school debate worldwide.',
            'body': (
                '<h2>Overview</h2>'
                '<p>The WSDC format is used at the World Schools Debating Championship and many national school-level '
                'circuits. Each team has three substantive speakers and a reply speaker.</p>'
                '<h2>Motions</h2>'
                '<p>WSDC tournaments use both prepared and impromptu motions. Teams receive prepared motions in advance '
                'and impromptu motions shortly before the debates begin.</p>'
                '<p>Full scoring breakdown and speaker role guides will be added soon.</p>'
            ),
        },
        {
            'title': 'How to Judge a BP Debate',
            'slug': 'how-to-judge-bp',
            'category': cats['judging'],
            'status': 'published',
            'reading_time_minutes': 5,
            'related_format_slugs': ['bp', 'british-parliamentary'],
            'summary': 'A practical guide for adjudicators new to BP debate — covering team ranking, speaker scores, and the principles of fair adjudication.',
            'body': (
                '<h2>The Adjudicator\'s Role</h2>'
                '<p>In BP debate, judges must rank all four teams from 1st to 4th place and assign individual speaker '
                'scores. The chair adjudicator leads the panel discussion and delivers the oral adjudication.</p>'
                '<h2>Key Principles</h2>'
                '<p>Judge the debate you saw, not the debate you wished to see. Evaluate arguments on their own merit, '
                'considering substantive content, strategy, and engagement with opposing arguments.</p>'
                '<p>Detailed rubrics and common judging pitfalls will be expanded here.</p>'
            ),
        },
        {
            'title': 'Speaker Scores: What the Numbers Mean',
            'slug': 'speaker-scores-guide',
            'category': cats['judging'],
            'status': 'published',
            'reading_time_minutes': 3,
            'related_format_slugs': ['bp', 'australs', 'wsdc'],
            'summary': 'Demystifying speaker score ranges — learn what constitutes an average, good, and excellent speech across major debate formats.',
            'body': (
                '<h2>Score Ranges</h2>'
                '<p>Speaker scores typically range from 50 to 100, with most speeches falling in the 70–80 range. '
                'The exact scale varies by tournament, but the relative meaning is consistent:</p>'
                '<ul>'
                '<li><strong>75–79:</strong> Average — competent, makes basic arguments</li>'
                '<li><strong>80–84:</strong> Good — clear structure, engages with opponents</li>'
                '<li><strong>85+:</strong> Excellent — innovative, persuasive, outstanding delivery</li>'
                '</ul>'
                '<p>More detailed breakdowns by format coming soon.</p>'
            ),
        },
        {
            'title': 'Building Strong Arguments in Debate',
            'slug': 'building-strong-arguments',
            'category': cats['training'],
            'status': 'published',
            'reading_time_minutes': 4,
            'related_format_slugs': ['bp', 'australs', 'wsdc'],
            'summary': 'Learn the fundamentals of argument construction — from assertion to reasoning to evidence — to make your debate speeches more persuasive.',
            'body': (
                '<h2>The ARE Framework</h2>'
                '<p>Every strong argument follows the Assertion–Reasoning–Evidence (ARE) structure:</p>'
                '<ol>'
                '<li><strong>Assertion:</strong> State your claim clearly</li>'
                '<li><strong>Reasoning:</strong> Explain why it\'s true using logic and mechanism</li>'
                '<li><strong>Evidence:</strong> Support with examples, data, or analogies</li>'
                '</ol>'
                '<h2>Common Mistakes</h2>'
                '<p>Assertion without reasoning is a claim, not an argument. Evidence without explanation is '
                'irrelevant name-dropping. Both are penalized by experienced judges.</p>'
                '<p>Advanced argumentation techniques and practice exercises will be added.</p>'
            ),
        },
        # DRAFT stubs (noindex, to be expanded later)
        {
            'title': 'How to Write a Good Motion',
            'slug': 'how-to-write-motions',
            'category': cats['hosting'],
            'status': 'draft',
            'reading_time_minutes': 5,
            'related_format_slugs': ['bp', 'australs'],
            'summary': 'Guidelines for crafting fair, debatable motions — including balance testing, clarity, and avoiding common pitfalls.',
            'body': '<p>This guide is under development. Check back soon for motion-writing best practices.</p>',
        },
        {
            'title': 'Organising Your First Debate Tournament',
            'slug': 'organising-first-tournament',
            'category': cats['hosting'],
            'status': 'draft',
            'reading_time_minutes': 6,
            'related_format_slugs': [],
            'summary': 'A step-by-step checklist for hosting a competitive debate tournament — from venue booking to tab release.',
            'body': '<p>This guide is under development. A comprehensive hosting checklist will be published here.</p>',
        },
        {
            'title': 'Points of Information (POIs): A Complete Guide',
            'slug': 'points-of-information-guide',
            'category': cats['training'],
            'status': 'draft',
            'reading_time_minutes': 3,
            'related_format_slugs': ['bp'],
            'summary': 'Master the art of giving and responding to Points of Information in parliamentary debate.',
            'body': '<p>This guide is under development. POI strategy and etiquette guides will be added soon.</p>',
        },
        {
            'title': 'The Role of the Chief Adjudicator',
            'slug': 'chief-adjudicator-role',
            'category': cats['judging'],
            'status': 'draft',
            'reading_time_minutes': 4,
            'related_format_slugs': [],
            'summary': 'What CAs do, how they set motions, manage panels, and ensure fair adjudication across a tournament.',
            'body': '<p>This guide is under development. CA responsibilities and best practices will be detailed here.</p>',
        },
        {
            'title': 'Using NekoTab to Run Your Tournament',
            'slug': 'using-nekotab-guide',
            'category': cats['hosting'],
            'status': 'draft',
            'reading_time_minutes': 5,
            'related_format_slugs': [],
            'summary': 'A walkthrough of NekoTab features — setting up, importing data, running rounds, and publishing results.',
            'body': '<p>This guide is under development. Step-by-step NekoTab tutorials will be published here.</p>',
        },
        {
            'title': 'Reply Speeches: Strategy and Structure',
            'slug': 'reply-speeches-guide',
            'category': cats['training'],
            'status': 'draft',
            'reading_time_minutes': 3,
            'related_format_slugs': ['australs', 'wsdc'],
            'summary': 'How to deliver an effective reply speech — structuring your summary, framing the debate, and maximizing impact.',
            'body': '<p>This guide is under development. Reply speech strategy and structure will be expanded here.</p>',
        },
    ]

    for stub in stubs:
        cat = stub.pop('category')
        Article.objects.create(category=cat, **stub)


def reverse_seed(apps, schema_editor):
    Article = apps.get_model('content', 'Article')
    Category = apps.get_model('content', 'ArticleCategory')
    Article.objects.all().delete()
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_content, reverse_seed),
    ]
