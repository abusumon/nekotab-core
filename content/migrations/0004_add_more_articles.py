"""Add additional high-quality articles to increase content depth for AdSense compliance."""
from django.db import migrations


def add_articles(apps, schema_editor):
    Article = apps.get_model('content', 'Article')
    Category = apps.get_model('content', 'ArticleCategory')

    cats = {}
    for cat in Category.objects.all():
        cats[cat.slug] = cat

    new_articles = [
        {
            'title': 'How to Prepare for a Debate Tournament',
            'slug': 'how-to-prepare-for-tournament',
            'category': cats.get('training'),
            'status': 'published',
            'reading_time_minutes': 8,
            'related_format_slugs': ['bp', 'australs', 'wsdc'],
            'summary': 'A complete preparation guide for competitive debaters — from research and casebuilding weeks before the tournament to warm-ups on the morning of competition.',
            'body': (
                '<h2>Why Preparation Matters</h2>'
                '<p>The difference between a good debater and a great one is rarely natural talent — it is preparation. '
                'While impromptu debating rewards quick thinking, the debaters who consistently perform well at tournaments '
                'are those who have invested time in building their knowledge base, practising their skills, and developing '
                'their strategic thinking long before they arrive at the venue.</p>'

                '<h2>Long-Term Preparation (Weeks Before)</h2>'

                '<h3>Build Your Knowledge Base</h3>'
                '<p>Competitive debate covers an enormous range of topics — from international relations to philosophy to economics '
                'to social policy. You do not need to be an expert in every field, but having a broad base of knowledge gives you '
                'a significant advantage. Here is how to build it:</p>'
                '<ul>'
                '<li><strong>Read widely:</strong> Follow quality news sources (The Economist, BBC, Al Jazeera, The Guardian) daily. '
                'Focus not just on what happened, but on the analysis of why it matters.</li>'
                '<li><strong>Study key debates:</strong> Familiarise yourself with the major arguments on both sides of enduring '
                'debates: capitalism vs. socialism, individual rights vs. collective welfare, interventionism vs. sovereignty.</li>'
                '<li><strong>Build an evidence bank:</strong> Keep a personal document organised by topic area with key statistics, '
                'case studies, and examples you can deploy in debates.</li>'
                '<li><strong>Watch expert debaters:</strong> YouTube hosts thousands of recorded debates from major tournaments. '
                'Study how top speakers structure arguments, handle POIs, and deliver reply speeches.</li>'
                '</ul>'

                '<h3>Practice Regularly</h3>'
                '<p>Attend your club\'s training sessions consistently. If your club meets weekly, try to add extra practice beyond that:</p>'
                '<ul>'
                '<li><strong>Practice debates:</strong> Nothing replaces the experience of actual debating. Aim for at least 2–3 '
                'practice debates per week in the lead-up to a tournament.</li>'
                '<li><strong>Solo drills:</strong> Practise impromptu casebuilding — pick a random motion, set a timer for 15 minutes, '
                'and construct a full case. Then deliver the first speaker speech to a mirror or recording device.</li>'
                '<li><strong>Rebuttal practice:</strong> Watch or listen to recorded speeches and practise delivering rebuttals. '
                'This builds your ability to respond quickly and effectively.</li>'
                '</ul>'

                '<h2>Short-Term Preparation (Days Before)</h2>'

                '<h3>Team Strategy</h3>'
                '<p>If you know your partner, spend time discussing your debating styles and preferences:</p>'
                '<ul>'
                '<li>Who prefers first speaker vs. second speaker?</li>'
                '<li>How will you split arguments during prep time?</li>'
                '<li>What is your strategy for closing halves (in BP)?</li>'
                '<li>What are each person\'s strongest topic areas?</li>'
                '</ul>'

                '<h3>Logistics</h3>'
                '<ul>'
                '<li>Confirm registration and check any published information about the tournament</li>'
                '<li>Prepare your materials: pen, paper, timer, water bottle, snacks</li>'
                '<li>Plan your travel — arrive early on the day, allowing time for registration and settling in</li>'
                '<li>Get a good night\'s sleep — mental sharpness is your most valuable asset</li>'
                '</ul>'

                '<h2>Tournament Day Preparation</h2>'

                '<h3>Before Round 1</h3>'
                '<ul>'
                '<li>Arrive 30 minutes before registration opens</li>'
                '<li>Check in with your partner and discuss any warm-up topics</li>'
                '<li>Review your evidence bank and refresh key statistics</li>'
                '<li>Do a quick warm-up: run through a practice motion in 5 minutes to activate your analytical thinking</li>'
                '</ul>'

                '<h3>Between Rounds</h3>'
                '<ul>'
                '<li>Debrief the previous round briefly — what worked, what did not</li>'
                '<li>Do not dwell on mistakes. Focus forward on the next debate.</li>'
                '<li>Stay hydrated and eat properly — cognitive performance drops sharply when you are hungry or dehydrated</li>'
                '<li>Review your evidence bank if you have time, focusing on topic areas you feel less confident about</li>'
                '</ul>'

                '<h2>Mental Preparation</h2>'
                '<p>Competitive debate is mentally demanding. Managing your mindset is as important as your substantive preparation:</p>'
                '<ul>'
                '<li><strong>Confidence, not arrogance:</strong> Believe in your preparation, but stay humble and open to learning</li>'
                '<li><strong>Process over results:</strong> Focus on executing your strategy well rather than fixating on wins</li>'
                '<li><strong>Handle losses gracefully:</strong> Every debater loses rounds. The best debaters learn from losses and '
                'move on quickly.</li>'
                '<li><strong>Support your partner:</strong> Debate is a team sport. Encourage each other and maintain positive energy.</li>'
                '</ul>'

                '<h2>Using NekoTab for Prep</h2>'
                '<p>NekoTab offers several tools that can enhance your tournament preparation:</p>'
                '<ul>'
                '<li><strong><a href="/motions-bank/">Motion Bank:</a></strong> Browse thousands of real tournament motions to practise '
                'casebuilding on topics from recent competitions</li>'
                '<li><strong><a href="/motions-bank/doctor/">Motion Doctor:</a></strong> Get AI-generated analysis of any motion, '
                'including argument suggestions, POI ideas, and difficulty assessments</li>'
                '<li><strong><a href="/forum/">Forum:</a></strong> Discuss strategies, share insights, and learn from other debaters '
                'in the community</li>'
                '</ul>'
            ),
        },
        {
            'title': 'Understanding Debate Adjudication Panels',
            'slug': 'understanding-adjudication-panels',
            'category': cats.get('judging'),
            'status': 'published',
            'reading_time_minutes': 7,
            'related_format_slugs': ['bp', 'australs', 'wsdc'],
            'summary': 'How adjudication panels work in competitive debate — chair and wing roles, panel deliberation, consensus vs. majority decisions, and how to disagree constructively.',
            'body': (
                '<h2>What Is an Adjudication Panel?</h2>'
                '<p>In competitive debate tournaments, most debates are not judged by a single person. Instead, a panel of adjudicators '
                '— typically consisting of a chair and one or two wing judges — evaluates the debate collectively. The panel system '
                'helps ensure fairness, reduces the impact of individual bias, and provides richer feedback to debaters.</p>'

                '<h2>Panel Composition</h2>'
                '<p>A typical adjudication panel has three members:</p>'
                '<ul>'
                '<li><strong>Chair adjudicator:</strong> The most experienced judge on the panel. Leads the deliberation, delivers the '
                'oral adjudication, and has the casting vote in case of a tie (in even-numbered panels).</li>'
                '<li><strong>Wing adjudicators:</strong> Support the chair by providing their independent assessment. Wings submit their '
                'own ranking and speaker scores, then participate in the panel discussion.</li>'
                '</ul>'
                '<p>At major tournaments, the most important debates (e.g., outround debates, high-powered preliminary rooms) may have '
                'panels of five or even seven judges. Less critical rooms may have solo chairs or panels of two.</p>'

                '<h2>The Chair\'s Role</h2>'
                '<p>Being a chair adjudicator carries specific responsibilities beyond simply judging the debate:</p>'
                '<ul>'
                '<li><strong>Before the debate:</strong> Introduce yourself and the wings to the debaters. Confirm the motion, '
                'format rules, and timing conventions. Ensure the room is set up properly.</li>'
                '<li><strong>During the debate:</strong> Take comprehensive notes. You will need to lead the discussion afterward, '
                'so your notes must cover all eight speeches (in BP) or all speeches in your format.</li>'
                '<li><strong>After the debate:</strong> Collect wings\' individual rankings before discussing. Lead a structured '
                'deliberation. Deliver the oral adjudication on behalf of the panel.</li>'
                '</ul>'

                '<h2>Panel Deliberation Process</h2>'
                '<p>After the debate ends, the panel follows this standard deliberation process:</p>'

                '<h3>Step 1: Independent Assessment</h3>'
                '<p>Each judge independently writes down their ranking (and, in some tournaments, tentative speaker scores) before any '
                'discussion begins. This prevents anchoring bias — where wing judges simply agree with the chair\'s first impression.</p>'

                '<h3>Step 2: Reveal Rankings</h3>'
                '<p>The chair asks each wing to share their ranking. This is done without justification first — just the numbers. '
                'This quickly tells the panel whether there is consensus or disagreement.</p>'

                '<h3>Step 3: Discuss Key Issues</h3>'
                '<p>The chair leads a discussion about the debate, focusing on:</p>'
                '<ul>'
                '<li>What were the key clashes or issues?</li>'
                '<li>Where do the panel members agree?</li>'
                '<li>Where do they disagree, and why?</li>'
                '</ul>'
                '<p>Good chairs encourage wings to explain their reasoning fully rather than simply deferring to the majority.</p>'

                '<h3>Step 4: Reach a Decision</h3>'
                '<p>The panel aims for consensus but uses majority voting when necessary. If the chair and one wing agree on a ranking, '
                'that becomes the panel\'s decision. The dissenting wing\'s call is recorded but not announced publicly.</p>'

                '<h3>Step 5: Oral Adjudication</h3>'
                '<p>The chair delivers the oral adjudication (oral adj), which should:</p>'
                '<ul>'
                '<li>Announce the ranking clearly</li>'
                '<li>Explain the key reasons for the decision</li>'
                '<li>Provide constructive feedback to each team</li>'
                '<li>Represent the panel\'s collective reasoning (even if the chair personally disagreed)</li>'
                '</ul>'

                '<h2>Handling Disagreements</h2>'
                '<p>Disagreements within panels are normal and healthy. Here is how to handle them constructively:</p>'
                '<ul>'
                '<li><strong>As a wing:</strong> Clearly explain your reasoning. Do not simply say "I disagree" — explain which '
                'specific argument or team assessment you see differently, and why. Be open to changing your mind if the chair '
                'or other wing presents a perspective you had not considered.</li>'
                '<li><strong>As a chair:</strong> Listen actively to dissenting views. Do not use your positional authority to '
                'override well-reasoned disagreements. If a wing makes a strong case, consider adjusting your own ranking.</li>'
                '<li><strong>For both:</strong> Focus on the arguments in the debate, not on each other. Deliberation should '
                'feel collaborative, not adversarial.</li>'
                '</ul>'

                '<h2>Common Panel Problems</h2>'
                '<ul>'
                '<li><strong>Chair dominance:</strong> When the chair announces their ranking first and wings feel pressured to agree. '
                'Solved by collecting independent rankings before discussion.</li>'
                '<li><strong>Over-long deliberation:</strong> Panels that spend 20+ minutes debating every minor point hold up the '
                'tournament. Focus on the key issues that determine the ranking.</li>'
                '<li><strong>Score inconsistency:</strong> Panel members using wildly different scoring scales. The chair should '
                'briefly calibrate scores before finalising.</li>'
                '<li><strong>Poor oral adjs from disagreement:</strong> When the chair is forced to explain a decision they disagreed '
                'with. Good chairs can still deliver a clear, fair oral adj even when they were in the minority.</li>'
                '</ul>'

                '<h2>Developing as a Panel Member</h2>'
                '<p>Whether you are a new wing or an aspiring chair, improving your panel skills requires:</p>'
                '<ul>'
                '<li>Judging as many rounds as possible across different panel positions</li>'
                '<li>Practising articulating your reasoning clearly and concisely</li>'
                '<li>Asking chairs for feedback after rounds — how could your contributions to deliberation improve?</li>'
                '<li>Being willing to change your mind when presented with strong reasoning</li>'
                '<li>Tracking your calls against panel decisions to identify blind spots in your judging</li>'
                '</ul>'
            ),
        },
        {
            'title': 'A Beginner\'s Guide to Competitive Debate',
            'slug': 'beginners-guide-competitive-debate',
            'category': cats.get('training'),
            'status': 'published',
            'reading_time_minutes': 9,
            'related_format_slugs': ['bp', 'australs', 'wsdc'],
            'summary': 'Everything a first-time debater needs to know — what competitive debate is, how tournaments work, essential skills to develop, and how to get started in your local circuit.',
            'body': (
                '<h2>What Is Competitive Debate?</h2>'
                '<p>Competitive debate is a structured intellectual sport where teams argue for or against a given proposition '
                '(called a "motion") in front of adjudicators who evaluate the quality of argumentation, strategy, and delivery. '
                'It is practised at university and school level in over 100 countries worldwide, with formats ranging from '
                'British Parliamentary (BP) to Australs to World Schools (WSDC).</p>'
                '<p>Unlike informal arguments, competitive debate has strict rules about speaking time, structure, and fairness. '
                'Teams often must argue positions they personally disagree with, which develops the ability to understand multiple '
                'perspectives — a skill valued in law, politics, business, journalism, and many other fields.</p>'

                '<h2>How a Debate Works</h2>'
                '<p>While formats vary, the basic structure of a competitive debate is consistent:</p>'
                '<ol>'
                '<li><strong>Motion announcement:</strong> The topic is revealed. In some rounds, it is announced just 15–30 '
                'minutes before the debate (impromptu); in others, teams know the topic weeks in advance (prepared).</li>'
                '<li><strong>Preparation time:</strong> Teams discuss strategy and build their case. In BP debate, this is '
                'typically 15 minutes.</li>'
                '<li><strong>Speeches:</strong> Each speaker delivers a timed speech — usually 7–8 minutes. Speakers present '
                'arguments, respond to opponents, and interact through Points of Information.</li>'
                '<li><strong>Adjudication:</strong> The judges deliberate and deliver a decision, providing feedback on each '
                'team\'s and speaker\'s performance.</li>'
                '</ol>'

                '<h2>Essential Skills for Debaters</h2>'
                '<p>Competitive debate develops a wide range of skills. Here are the core competencies that every debater should '
                'work on:</p>'

                '<h3>1. Argument Construction</h3>'
                '<p>The ability to build logical, well-supported arguments is the foundation of debate. Use the ARE framework: '
                'make an <strong>Assertion</strong>, provide <strong>Reasoning</strong> (the logical mechanism), and support '
                'with <strong>Evidence</strong> (examples, data, analogies). Judges reward arguments that are specific, '
                'well-reasoned, and responsive to the motion.</p>'

                '<h3>2. Rebuttal</h3>'
                '<p>Rebuttal is the art of responding to opposing arguments. Effective rebuttal does not merely deny the '
                'opponent\'s claims — it explains <em>why</em> they are wrong. Strong rebuttals attack the reasoning or '
                'evidence behind an argument, not just the conclusion. The best debaters make their opponents\' arguments '
                'sound unreasonable even to neutral listeners.</p>'

                '<h3>3. Critical Thinking</h3>'
                '<p>Debate trains you to think quickly and analytically under pressure. You must evaluate arguments in real-time, '
                'identify logical flaws, spot false analogies, and distinguish between correlation and causation. These skills '
                'transfer directly to academic writing, professional decision-making, and everyday reasoning.</p>'

                '<h3>4. Public Speaking</h3>'
                '<p>Persuasive delivery amplifies strong arguments. Work on clarity, pace, volume, and eye contact. The best '
                'debaters sound confident but not aggressive, passionate but not unhinged. Your manner should serve your content — '
                'not distract from it.</p>'

                '<h3>5. Teamwork</h3>'
                '<p>Debate is a team sport. You must coordinate with your partner (or partners, depending on the format) — '
                'splitting arguments, covering each other\'s weaknesses, and presenting a unified case. Good team dynamics '
                'make the whole greater than the sum of its parts.</p>'

                '<h2>How Tournaments Work</h2>'
                '<p>A typical debate tournament consists of:</p>'
                '<ul>'
                '<li><strong>Preliminary rounds (3–7 rounds):</strong> All teams debate against different opponents in each '
                'round. Motions are usually impromptu and announced before each round.</li>'
                '<li><strong>Break rounds (quarter-finals, semi-finals, final):</strong> The top-performing teams from '
                'preliminary rounds advance to elimination rounds. Break rounds often have prepared motions.</li>'
                '<li><strong>Speaker awards:</strong> Individual speakers are ranked by their cumulative scores across all '
                'preliminary rounds.</li>'
                '</ul>'
                '<p>Tournaments typically run over 1–3 days, with 1–2 day competitions being most common for local circuit events.</p>'

                '<h2>Getting Started</h2>'
                '<p>If you are interested in competitive debate, here is how to begin:</p>'

                '<h3>Join a Society</h3>'
                '<p>Most universities and many schools have debating societies that welcome beginners. These clubs run regular '
                'training sessions, internal competitions, and attend external tournaments. Search for a debating society at your '
                'institution — it is the easiest way to start.</p>'

                '<h3>Attend a Tournament as a Novice</h3>'
                '<p>Many tournaments have novice or beginner categories specifically for first-time debaters. These provide a '
                'lower-pressure environment to experience competitive debating with opponents of similar experience levels.</p>'

                '<h3>Watch and Learn</h3>'
                '<p>Recorded debates from major tournaments are widely available on YouTube. Search for WUDC, Australs, or '
                'national championship finals to see expert-level debate. Pay attention to how speakers structure their '
                'arguments, handle challenges, and manage their time.</p>'

                '<h3>Use NekoTab\'s Resources</h3>'
                '<p>NekoTab provides several free tools to support your debate journey:</p>'
                '<ul>'
                '<li><strong><a href="/motions-bank/">Motion Bank:</a></strong> Browse thousands of real tournament motions for practice</li>'
                '<li><strong><a href="/motions-bank/doctor/">Motion Doctor:</a></strong> Get AI analysis of any motion — great for '
                'self-study and preparation</li>'
                '<li><strong><a href="/learn/">Learn Hub:</a></strong> Guides on formats, judging, argumentation, and more</li>'
                '<li><strong><a href="/forum/">Forum:</a></strong> Join discussions with debaters from around the world</li>'
                '</ul>'

                '<h2>Common Beginner Mistakes</h2>'
                '<p>Every debater makes mistakes early on. Being aware of these common pitfalls helps you improve faster:</p>'
                '<ul>'
                '<li><strong>Assertion without reasoning:</strong> Stating claims without explaining why they are true. '
                'Always answer the question "why?" after making a point.</li>'
                '<li><strong>Ignoring the other side:</strong> Spending all your time on your own arguments without engaging '
                'with what your opponents said. Judges need to see clash.</li>'
                '<li><strong>Speaking too fast:</strong> Nervousness often leads to rapid speech. Slow down, breathe, and '
                'prioritise clarity over volume of content.</li>'
                '<li><strong>Being afraid to be wrong:</strong> You will argue positions you find uncomfortable. Embrace it — '
                'the ability to argue any side of an issue is the whole point of debate training.</li>'
                '<li><strong>Not taking POIs:</strong> Refusing all Points of Information signals weakness. Take at least one '
                'per speech and respond confidently.</li>'
                '</ul>'

                '<h2>The Debate Community</h2>'
                '<p>One of the best things about competitive debate is the community. Debating circuits around the world are '
                'welcoming, intellectually stimulating, and socially rewarding. Tournaments are as much about socialising, '
                'networking, and building friendships as they are about competition. Many of the relationships formed through '
                'debate last a lifetime.</p>'
                '<p>Welcome to the world of competitive debate — your first tournament is just the beginning.</p>'
            ),
        },
    ]

    for data in new_articles:
        cat = data.pop('category')
        if not Article.objects.filter(slug=data['slug']).exists():
            Article.objects.create(category=cat, **data)


def reverse_add(apps, schema_editor):
    Article = apps.get_model('content', 'Article')
    slugs = [
        'how-to-prepare-for-tournament',
        'understanding-adjudication-panels',
        'beginners-guide-competitive-debate',
    ]
    Article.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0003_expand_articles'),
    ]

    operations = [
        migrations.RunPython(add_articles, reverse_add),
    ]
