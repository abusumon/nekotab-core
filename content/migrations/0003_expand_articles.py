"""Expand article stubs with full, high-quality content for AdSense compliance.
Publishes all draft articles with substantial unique content (800+ words each).
Removes all 'coming soon' placeholder text."""
from django.db import migrations


def expand_articles(apps, schema_editor):
    Article = apps.get_model('content', 'Article')

    # ── Map of slug → full body content ──
    updates = {
        'what-is-bp-debate': {
            'status': 'published',
            'reading_time_minutes': 8,
            'summary': 'A comprehensive introduction to British Parliamentary debate — the most widely used format in university-level competitive debating worldwide. Learn about the structure, speaker roles, extensions, and scoring.',
            'body': (
                '<h2>Overview</h2>'
                '<p>British Parliamentary (BP) debate is the most widely used competitive debating format at the university level worldwide. '
                'It is the official format of the World Universities Debating Championship (WUDC) and is used by debating circuits across Europe, '
                'Asia, Africa, and the Americas. The format features four teams of two speakers each, making for dynamic, fast-paced debates '
                'with eight speeches in every round.</p>'

                '<h2>The Four Teams</h2>'
                '<p>In every BP debate, there are four teams divided into two sides:</p>'
                '<ul>'
                '<li><strong>Opening Government (OG):</strong> Sets up the case for the proposition. The Prime Minister defines the motion '
                'and presents the government\'s main arguments. The Deputy Prime Minister rebuilds the case and responds to the opposition.</li>'
                '<li><strong>Opening Opposition (OO):</strong> Directly clashes with the Opening Government. The Leader of the Opposition '
                'provides the main opposition arguments, and the Deputy Leader of the Opposition deepens the opposition case.</li>'
                '<li><strong>Closing Government (CG):</strong> Must introduce an "extension" — a new, substantive argument that adds '
                'to the government\'s side without contradicting Opening Government. The Member of the Government presents the extension, '
                'and the Government Whip summarises the entire government case.</li>'
                '<li><strong>Closing Opposition (CO):</strong> Similarly introduces an opposition extension. The Member of the Opposition '
                'presents it, and the Opposition Whip delivers the final opposition summary.</li>'
                '</ul>'

                '<h2>Speaking Order and Times</h2>'
                '<p>Each speaker delivers a 7-minute speech. The standard speaking order is:</p>'
                '<ol>'
                '<li>Prime Minister (OG) — 7 minutes</li>'
                '<li>Leader of the Opposition (OO) — 7 minutes</li>'
                '<li>Deputy Prime Minister (OG) — 7 minutes</li>'
                '<li>Deputy Leader of the Opposition (OO) — 7 minutes</li>'
                '<li>Member of the Government (CG) — 7 minutes</li>'
                '<li>Member of the Opposition (CO) — 7 minutes</li>'
                '<li>Government Whip (CG) — 7 minutes</li>'
                '<li>Opposition Whip (CO) — 7 minutes</li>'
                '</ol>'
                '<p>Points of Information (POIs) may be offered during the middle five minutes of each speech — '
                'the first and last minutes are "protected time" when POIs are not permitted.</p>'

                '<h2>What Is an Extension?</h2>'
                '<p>The extension is what makes BP debate unique. Closing teams cannot simply repeat or rephrase what their opening half said. '
                'They must bring a genuinely new argument, perspective, or analysis that substantively adds to their side of the debate. '
                'A strong extension often provides a new stakeholder analysis, a different mechanism, or a deeper principle-based argument '
                'that the opening half missed.</p>'
                '<p>Judges evaluate whether the extension is truly new, whether it is well-developed, and whether it contributes meaningfully '
                'to the side\'s overall case. A closing team that merely summarises without extending will almost always be ranked below '
                'a closing team that introduces compelling new material.</p>'

                '<h2>Judging and Ranking</h2>'
                '<p>Adjudicators rank all four teams from 1st to 4th place. They also assign individual speaker scores, typically on a scale '
                'where 75–79 represents an average speech, 80–84 a good speech, and 85+ an excellent speech. The ranking reflects the overall '
                'persuasiveness and strategic contribution of each team.</p>'
                '<p>Key criteria for ranking include:</p>'
                '<ul>'
                '<li><strong>Argumentation:</strong> Are the arguments logical, well-structured, and supported by reasoning and examples?</li>'
                '<li><strong>Engagement:</strong> Does the team effectively respond to opponents\' arguments through rebuttal?</li>'
                '<li><strong>Strategy:</strong> Is the team\'s overall approach coherent and well-timed?</li>'
                '<li><strong>Extension quality:</strong> For closing teams, is the extension substantive and impactful?</li>'
                '</ul>'

                '<h2>Points of Information</h2>'
                '<p>POIs are a hallmark of parliamentary debate. During the middle five minutes of any speech, members of opposing teams may '
                'stand and offer a brief interjection — typically a question or counter-point lasting no more than 15 seconds. The speaker '
                'has the right to accept or decline, but taking at least one or two POIs is expected and rewarded by judges.</p>'
                '<p>Effective POIs can disrupt an opponent\'s line of reasoning, highlight weaknesses, or set up arguments for your own side. '
                'Accepting and handling POIs gracefully demonstrates confidence and depth of understanding.</p>'

                '<h2>Why BP Is Popular</h2>'
                '<p>BP debate has become the global standard for several reasons:</p>'
                '<ul>'
                '<li><strong>Inclusivity:</strong> Four teams per debate means more debaters can participate in each round.</li>'
                '<li><strong>Skill development:</strong> Closing teams must listen, adapt, and innovate under pressure.</li>'
                '<li><strong>Dynamic competition:</strong> The four-team structure creates varied competitive dynamics beyond simple head-to-head clashes.</li>'
                '<li><strong>Global community:</strong> As the WUDC format, it connects debaters from over 100 countries.</li>'
                '</ul>'

                '<h2>Getting Started with BP</h2>'
                '<p>If you are new to BP debate, the best way to learn is by attending training sessions at your local debating society, '
                'watching recorded debates from major tournaments (many are available on YouTube), and practicing regularly with teammates. '
                'Familiarise yourself with the speaker roles, practice constructing extensions, and study how experienced debaters handle POIs.</p>'
                '<p>NekoTab\'s <a href="/motions-bank/">Motion Bank</a> provides thousands of real BP motions from tournaments worldwide — '
                'perfect for practice and preparation. You can also use the <a href="/motions-bank/doctor/">Motion Doctor</a> for AI-powered '
                'analysis of any motion, including clash maps, strategies, and difficulty ratings.</p>'
            ),
        },

        'australs-3v3-format': {
            'status': 'published',
            'reading_time_minutes': 7,
            'summary': 'Learn about the Australs (3v3) debate format — a two-team structure with three speakers per side widely used in Asia-Pacific debate circuits. Covers structure, roles, reply speeches, and strategy.',
            'body': (
                '<h2>Overview</h2>'
                '<p>The Australs format, also known as 3v3 or Asian Parliamentary format, is a two-team debate structure featuring three '
                'speakers per side. It is the standard format for the Australasian Intervarsity Debating Championships (Australs), many '
                'Asian debating competitions, and national circuits across the Asia-Pacific region and beyond.</p>'

                '<h2>Structure and Speaking Order</h2>'
                '<p>Each debate features six substantive speeches and two reply speeches:</p>'
                '<ol>'
                '<li><strong>First Affirmative (1A):</strong> Defines the motion, establishes the team\'s case framework, and presents '
                'the first major argument. This speaker sets the parameters of the debate.</li>'
                '<li><strong>First Negative (1N):</strong> Responds to the definition (if necessary), outlines the negative case, and '
                'presents the negative\'s first argument while rebutting the affirmative.</li>'
                '<li><strong>Second Affirmative (2A):</strong> Rebuts the negative case, rebuilds the affirmative case where attacked, '
                'and presents additional arguments.</li>'
                '<li><strong>Second Negative (2N):</strong> Continues rebuttal of the affirmative case then presents further negative arguments.</li>'
                '<li><strong>Third Affirmative (3A):</strong> The final substantive speaker for the affirmative. Focuses heavily on '
                'rebuttal and crystallisation — identifying the key clashes in the debate and explaining why the affirmative wins them.</li>'
                '<li><strong>Third Negative (3N):</strong> The final substantive speaker for the negative. Like the 3A, focuses on '
                'rebuttal, clash identification, and explaining why the negative team has won the debate.</li>'
                '<li><strong>Reply Speech (Negative):</strong> Delivered by either the 1N or 2N. A shorter speech (typically 4–5 minutes) '
                'that summarises the debate from the negative\'s perspective.</li>'
                '<li><strong>Reply Speech (Affirmative):</strong> Delivered by either the 1A or 2A. The final word in the debate, '
                'summarising the affirmative\'s case and key clashes.</li>'
                '</ol>'
                '<p>Substantive speeches are typically 7–8 minutes. Reply speeches are 4–5 minutes. The reply speech order is reversed — '
                'the negative replies first, giving the affirmative the final word.</p>'

                '<h2>Key Differences from BP</h2>'
                '<p>Understanding the differences between Australs and BP is essential for debaters who compete in both formats:</p>'
                '<ul>'
                '<li><strong>Two teams, not four:</strong> There are no closing halves or extensions needed.</li>'
                '<li><strong>Deeper clash:</strong> With only two teams, engagement between the teams tends to be more direct and sustained.</li>'
                '<li><strong>Reply speeches:</strong> These short summary speeches are unique to Australs and require a different skill set — '
                'the ability to zoom out, identify the most important issues, and explain the debate as a narrative.</li>'
                '<li><strong>Third speakers as clash-drivers:</strong> The third speaker role in Australs is distinct — they rarely introduce '
                'new arguments and instead focus on crystallisation and deep rebuttal.</li>'
                '<li><strong>Win/loss outcome:</strong> Unlike BP\'s four-way ranking, Australs debates have a clear winner and loser.</li>'
                '</ul>'

                '<h2>The Reply Speech</h2>'
                '<p>The reply speech is one of the most challenging and distinctive elements of Australs debating. It is a shorter speech '
                '(usually 4–5 minutes) delivered after all substantive speeches. The speaker must:</p>'
                '<ul>'
                '<li>Identify the 2–3 most important clashes or issues in the debate</li>'
                '<li>Explain the debate from a "bird\'s-eye view" — not rehashing individual arguments, but framing the overall narrative</li>'
                '<li>Demonstrate why their team won the key clashes</li>'
                '<li>Avoid introducing new arguments (new arguments in the reply speech are typically disregarded by judges)</li>'
                '</ul>'
                '<p>A strong reply speech can significantly influence how judges perceive the debate. It is an opportunity to control the '
                'narrative and ensure that your team\'s strongest points are top-of-mind for adjudicators.</p>'

                '<h2>Adjudication in Australs</h2>'
                '<p>Judges in Australs debates deliver a binary verdict — one team wins and one team loses. Speaker scores are assigned '
                'individually, and oral adjudications explain the key reasons for the decision. Panels typically consist of a chair and '
                'two wings, with majority verdicts when there is disagreement.</p>'
                '<p>Adjudicators evaluate:</p>'
                '<ul>'
                '<li>The quality and depth of argumentation on each side</li>'
                '<li>Effective rebuttal — did each team engage with the strongest version of their opponents\' arguments?</li>'
                '<li>Crystallisation — did the third speakers and reply speakers identify the right issues?</li>'
                '<li>Manner and delivery — was the speaking persuasive, clear, and well-paced?</li>'
                '</ul>'

                '<h2>Strategy Tips for Australs</h2>'
                '<p>Success in Australs requires careful team coordination. Before the debate begins, teams should agree on:</p>'
                '<ul>'
                '<li>A clear case split — how arguments are divided between 1st and 2nd speakers</li>'
                '<li>The overall theme or narrative for their case</li>'
                '<li>Who will deliver the reply speech and how they will prepare it during the debate</li>'
                '</ul>'
                '<p>During the debate, listening is as important as speaking. Third speakers must take detailed notes on all six '
                'substantive speeches to deliver effective crystallisation. Reply speakers must synthesise the entire debate into a '
                'coherent, persuasive summary.</p>'

                '<h2>Where Australs Is Used</h2>'
                '<p>The Australs format is the primary competitive format in:</p>'
                '<ul>'
                '<li>Australia and New Zealand (Australasian Intervarsity Debating Championships)</li>'
                '<li>Southeast Asia (United Asian Debating Championships and national circuits)</li>'
                '<li>South Asia (many national and regional competitions)</li>'
                '<li>Parts of Africa and the Middle East</li>'
                '</ul>'
                '<p>Many debaters compete in both Australs and BP, and the skills transfer well between formats. NekoTab supports '
                'full Australs tabulation including side allocation, speaker score tracking, and break calculations.</p>'
            ),
        },

        'wsdc-format-explained': {
            'status': 'published',
            'reading_time_minutes': 7,
            'summary': 'An overview of the World Schools Debating Championship (WSDC) format — the premier format for high school debate worldwide. Covers structure, motions, scoring, and preparation tips.',
            'body': (
                '<h2>Overview</h2>'
                '<p>The World Schools Debating Championship (WSDC) format is the standard for competitive debating at the secondary school '
                'level. Used at the annual World Schools Debating Championship and adopted by national circuits in over 60 countries, it '
                'combines elements of prepared and impromptu debating, testing both research skills and adaptability.</p>'

                '<h2>Structure</h2>'
                '<p>A WSDC debate features two teams — Proposition and Opposition — with three substantive speakers and a reply speaker on each side:</p>'
                '<ol>'
                '<li><strong>First Proposition:</strong> Defines the motion, sets up the case framework, and presents opening arguments (8 minutes)</li>'
                '<li><strong>First Opposition:</strong> Responds to the definition, outlines the opposition case, and presents initial arguments (8 minutes)</li>'
                '<li><strong>Second Proposition:</strong> Rebuts opposition arguments, rebuilds case, presents further arguments (8 minutes)</li>'
                '<li><strong>Second Opposition:</strong> Continues rebuttal, strengthens opposition case (8 minutes)</li>'
                '<li><strong>Third Proposition:</strong> Final substantive speaker — focuses on rebuttal and crystallisation (8 minutes)</li>'
                '<li><strong>Third Opposition:</strong> Final substantive speaker — rebuttal and crystallisation (8 minutes)</li>'
                '<li><strong>Opposition Reply:</strong> Summary from opposition perspective — delivered by 1st or 2nd speaker (4 minutes)</li>'
                '<li><strong>Proposition Reply:</strong> Final speech in the debate — summary from proposition perspective (4 minutes)</li>'
                '</ol>'

                '<h2>Prepared vs. Impromptu Motions</h2>'
                '<p>One of the unique features of WSDC is the use of both prepared and impromptu motions:</p>'
                '<ul>'
                '<li><strong>Prepared motions:</strong> Released weeks or months before the tournament. Teams research extensively and can '
                'bring prepared cases. This rewards depth of research and case construction.</li>'
                '<li><strong>Impromptu motions:</strong> Released 30 minutes to 1 hour before the debate. Teams must construct their case '
                'on the spot, testing their general knowledge, analytical thinking, and ability to work under pressure.</li>'
                '</ul>'
                '<p>Most WSDC tournaments alternate between prepared and impromptu rounds, ensuring that both skill sets are tested.</p>'

                '<h2>Scoring in WSDC</h2>'
                '<p>WSDC uses a detailed marking system where each speech is scored on three criteria:</p>'
                '<ul>'
                '<li><strong>Content (40%):</strong> The quality, relevance, and depth of arguments and rebuttals</li>'
                '<li><strong>Style (40%):</strong> Persuasiveness, clarity, and engagement of delivery</li>'
                '<li><strong>Strategy (20%):</strong> Structure, time management, and responsiveness to the debate dynamics</li>'
                '</ul>'
                '<p>Individual speaker scores typically range from 60 to 80 out of 100, with most speeches falling between 70 and 78. '
                'Team scores are aggregated to determine the winner, with the team accumulating more total points winning the debate.</p>'

                '<h2>Points of Information</h2>'
                '<p>Like other parliamentary formats, WSDC allows Points of Information during the middle portion of substantive speeches. '
                'The first and last minutes of each 8-minute speech are protected time. POIs must be brief (under 15 seconds) and speakers '
                'should take at least one or two per speech. Judges evaluate both the quality of POIs offered and how well speakers handle them.</p>'

                '<h2>The Role of the Third Speaker</h2>'
                '<p>The third speaker in WSDC has a unique role. While they may introduce a final argument, their primary responsibility is:</p>'
                '<ul>'
                '<li>Providing thorough rebuttal of the opposing team\'s strongest arguments</li>'
                '<li>Identifying the key clashes and explaining why their team wins them</li>'
                '<li>Crystallising the debate — showing the big picture of why their side is correct</li>'
                '</ul>'
                '<p>An effective third speaker transforms scattered arguments and rebuttals into a coherent narrative that makes the judge\'s '
                'decision easier.</p>'

                '<h2>Preparing for WSDC Tournaments</h2>'
                '<p>Preparation for WSDC tournaments involves:</p>'
                '<ul>'
                '<li><strong>Research:</strong> For prepared motions, teams should research both sides thoroughly, preparing case files with '
                'evidence, examples, and anticipated counter-arguments</li>'
                '<li><strong>Practice improvisation:</strong> Regular impromptu debate practice builds the analytical muscles needed for '
                'impromptu rounds</li>'
                '<li><strong>Case file development:</strong> Organised folders of arguments, evidence, and rebuttals for prepared topics</li>'
                '<li><strong>Reply speech drills:</strong> Practise delivering 4-minute summaries of practice debates to develop this '
                'critical skill</li>'
                '</ul>'

                '<h2>WSDC Around the World</h2>'
                '<p>The WSDC format is used at the annual World Schools Debating Championship, which brings together national teams from '
                'over 60 countries. It is also the standard format for many national school debating competitions, including those in the '
                'United Kingdom, Australia, South Africa, Thailand, and many other countries.</p>'
                '<p>NekoTab provides full tabulation support for WSDC tournaments, including prepared and impromptu round management, '
                'side allocation, and comprehensive speaker and team standings.</p>'
            ),
        },

        'how-to-judge-bp': {
            'status': 'published',
            'reading_time_minutes': 9,
            'summary': 'A practical guide for adjudicators new to BP debate — covering team ranking, speaker scores, the principles of fair adjudication, common mistakes, and how to deliver clear oral adjudications.',
            'body': (
                '<h2>The Adjudicator\'s Role</h2>'
                '<p>In British Parliamentary debate, adjudicators have a critical responsibility: to evaluate the debate fairly and '
                'transparently. Every round involves ranking four teams from 1st to 4th place and assigning individual speaker scores. '
                'The chair adjudicator leads the panel discussion and delivers the oral adjudication (oral adj) explaining the decision.</p>'

                '<h2>Before the Round</h2>'
                '<p>Good adjudication starts before the speeches begin:</p>'
                '<ul>'
                '<li>Arrive on time and introduce yourself to other panel members</li>'
                '<li>Read the motion carefully and consider what a reasonable range of interpretations might look like</li>'
                '<li>Prepare your note-taking system — whether you use a split-page format, abbreviations, or shorthand, consistency is key</li>'
                '<li>Clear any biases: decide to judge the debate you see, not the debate you expected</li>'
                '</ul>'

                '<h2>During the Speeches</h2>'
                '<p>While speakers present their cases, effective judges:</p>'
                '<ul>'
                '<li><strong>Take structured notes:</strong> Write down each speaker\'s main arguments, rebuttals, and POIs. Note which '
                'arguments were rebutted and whether the rebuttal was effective</li>'
                '<li><strong>Track engagement:</strong> Did each team respond to the strongest version of their opponents\' case, or did '
                'they pick easy targets?</li>'
                '<li><strong>Assess extensions:</strong> For closing teams, note whether the extension is genuinely new and well-developed</li>'
                '<li><strong>Note manner:</strong> Delivery matters — was the speaker clear, confident, and persuasive? Did they use '
                'their speaking time effectively?</li>'
                '</ul>'

                '<h2>Ranking Teams: The Fundamentals</h2>'
                '<p>After all eight speeches, you must rank the four teams from 1st to 4th. Here is a practical framework:</p>'
                '<ol>'
                '<li><strong>Identify the key issues in the debate:</strong> What were the 2–3 most important clashes? These are the '
                'questions on which the debate hinged.</li>'
                '<li><strong>Assess each team\'s contribution to those issues:</strong> Who made the most persuasive arguments? Who '
                'provided the strongest rebuttals? Who won the key clashes?</li>'
                '<li><strong>Compare opening vs. closing halves:</strong> Did closing teams add value through their extensions, or did '
                'they merely repeat the opening half?</li>'
                '<li><strong>Determine the ranking:</strong> The team that was most persuasive on the most important issues should be '
                'ranked 1st, and so on.</li>'
                '</ol>'

                '<h2>Speaker Scores</h2>'
                '<p>Speaker scores reflect individual speaking quality. While different tournaments use slightly different scales, '
                'a common benchmark is:</p>'
                '<ul>'
                '<li><strong>Below 73:</strong> Significantly below average — major structural or content issues</li>'
                '<li><strong>73–76:</strong> Below average — some arguments but lacking depth or engagement</li>'
                '<li><strong>77–79:</strong> Average — competent speech with basic arguments and some rebuttal</li>'
                '<li><strong>80–82:</strong> Good — well-structured, engaging, and persuasive</li>'
                '<li><strong>83–85:</strong> Very good — outstanding arguments, strong rebuttal, excellent delivery</li>'
                '<li><strong>86+:</strong> Exceptional — a speech that would be competitive at the highest international level</li>'
                '</ul>'
                '<p>Speaker scores should be consistent within a debate — the best speaker in the room should have the highest score, '
                'regardless of which team they are on.</p>'

                '<h2>Panel Deliberation</h2>'
                '<p>In most BP tournaments, panels consist of a chair and one or two wing judges. After the debate:</p>'
                '<ol>'
                '<li>Wing judges submit their individual rankings to the chair</li>'
                '<li>The chair leads a discussion about the key issues and each team\'s performance</li>'
                '<li>The panel aims for consensus but uses majority voting when consensus is not possible</li>'
                '<li>The chair delivers the oral adjudication on behalf of the panel</li>'
                '</ol>'
                '<p>If you are a wing judge who disagrees with the majority, you may still express your view in a "shadow call" — '
                'recorded but not announced publicly.</p>'

                '<h2>Delivering the Oral Adjudication</h2>'
                '<p>A good oral adj should:</p>'
                '<ul>'
                '<li>Start by announcing the ranking (1st through 4th)</li>'
                '<li>Explain the key issues the panel identified</li>'
                '<li>Explain why each team was ranked where they were, focusing on substantive reasons</li>'
                '<li>Be constructive — offer advice that helps speakers improve</li>'
                '<li>Be concise — aim for 5–10 minutes, not a re-hash of the entire debate</li>'
                '</ul>'

                '<h2>Common Adjudication Mistakes</h2>'
                '<p>Avoid these pitfalls that lead to poor judging:</p>'
                '<ul>'
                '<li><strong>Interventionism:</strong> Judging based on your own opinion about the motion rather than the arguments presented</li>'
                '<li><strong>Content bias:</strong> Rewarding teams that argue the side you personally agree with</li>'
                '<li><strong>Manner override:</strong> Ranking a team higher solely because they were entertaining, despite weaker arguments</li>'
                '<li><strong>Ignoring extensions:</strong> Failing to distinguish between closing teams that extended and those that merely repeated</li>'
                '<li><strong>Hindsight rebuttal:</strong> Penalising a team for not making an argument you thought of, rather than evaluating '
                'what was actually said</li>'
                '</ul>'

                '<h2>Improving as a Judge</h2>'
                '<p>The best way to become a better adjudicator is consistent practice and feedback:</p>'
                '<ul>'
                '<li>Judge as many rounds as possible, especially alongside experienced adjudicators</li>'
                '<li>Ask for feedback on your oral adjudications</li>'
                '<li>Watch recorded debates and practice ranking teams before seeing the official decision</li>'
                '<li>Read judging guides from major tournaments (WUDCs often publish adjudication handbooks)</li>'
                '</ul>'
            ),
        },

        'speaker-scores-guide': {
            'status': 'published',
            'reading_time_minutes': 6,
            'summary': 'Demystifying speaker score ranges — learn what constitutes an average, good, and excellent speech across major debate formats, and how judges should calibrate their scores.',
            'body': (
                '<h2>Why Speaker Scores Matter</h2>'
                '<p>Speaker scores are more than just numbers on a tab sheet. They determine individual speaker rankings, influence '
                'break calculations, and provide crucial feedback to debaters about their performance. Understanding what the numbers '
                'mean — and how to assign them consistently — is essential for both judges and debaters.</p>'

                '<h2>The Standard Scale</h2>'
                '<p>Most parliamentary debate tournaments use a speaker score scale that runs from approximately 50 to 100, though the '
                'practical range is usually much narrower. Here is a detailed breakdown of what each score range typically represents:</p>'

                '<h3>Below 70 — Well Below Average</h3>'
                '<p>Scores in this range indicate major issues with the speech. The speaker may have struggled to complete their time, '
                'provided no coherent arguments, or displayed severe structural problems. These scores are rare and should be used '
                'sparingly — they signal that the speech was significantly deficient.</p>'

                '<h3>70–74 — Below Average</h3>'
                '<p>The speaker made some attempt at argumentation but fell short in key areas. Arguments may have been superficial, '
                'poorly explained, or largely unresponsive to the debate. Delivery may have been unclear or disengaged. This range '
                'is appropriate for speeches that show basic competence but lack depth.</p>'

                '<h3>75–79 — Average</h3>'
                '<p>This is the most common scoring range and represents a competent speech. The speaker presented identifiable arguments '
                'with some reasoning and examples, engaged at least partially with opponents, and demonstrated adequate delivery. '
                'Most speeches in a typical university tournament fall in this range.</p>'

                '<h3>80–84 — Good</h3>'
                '<p>A good speech demonstrates clear structure, well-reasoned arguments supported by specific examples, effective '
                'rebuttal that addresses the strongest opposing points, and engaging delivery. Speakers in this range show strong '
                'analytical ability and persuasive skill. These scores are appropriate for speakers who stand out in a round.</p>'

                '<h3>85–89 — Very Good to Excellent</h3>'
                '<p>Speeches in this range are exceptional. The speaker presents innovative arguments with deep analysis, provides '
                'devastating rebuttal, demonstrates mastery of the debate dynamics, and delivers with confidence and flair. These scores '
                'should be reserved for performances that would be competitive at national or international level.</p>'

                '<h3>90+ — Outstanding</h3>'
                '<p>Scores above 90 are exceedingly rare and signal a truly remarkable speech — the kind of performance that would be '
                'remembered as one of the best at a major international tournament. Judges should be very cautious about assigning '
                'these scores to maintain scale integrity.</p>'

                '<h2>Calibration Across Formats</h2>'
                '<p>Different debate formats and circuits may use slightly different scoring conventions:</p>'
                '<ul>'
                '<li><strong>BP (British Parliamentary):</strong> Most tournaments centre scores around 75, with top speakers in a '
                'tournament averaging around 80–82.</li>'
                '<li><strong>Australs:</strong> Similar to BP, though some circuits use 70 as the centre point.</li>'
                '<li><strong>WSDC:</strong> Uses a percentage-based system with content (40%), style (40%), and strategy (20%) '
                'components, scored out of 100.</li>'
                '</ul>'
                '<p>Always check the tournament\'s judging briefing for specific scale guidance. Consistency within a tournament is '
                'more important than matching external benchmarks.</p>'

                '<h2>Common Scoring Mistakes</h2>'
                '<p>Judges should avoid these common pitfalls when assigning speaker scores:</p>'
                '<ul>'
                '<li><strong>Score compression:</strong> Assigning all speakers between 76 and 78, making it impossible to distinguish '
                'performance. Use the full range.</li>'
                '<li><strong>Team-rank anchoring:</strong> Automatically giving the top-ranked team\'s speakers the highest scores. '
                'A strong individual speaker on a losing team can and should outscore a weaker speaker on a winning team.</li>'
                '<li><strong>Inconsistency:</strong> Scoring higher in later rounds because you\'ve seen "better" debates. Control for '
                'round-to-round drift by keeping your overall averages consistent.</li>'
                '<li><strong>Punishment scoring:</strong> Using abnormally low scores to "punish" rule violations or poor behaviour. '
                'Address these through tournament mechanisms, not the scorecard.</li>'
                '</ul>'

                '<h2>Tips for Debaters</h2>'
                '<p>Understanding speaker scores helps you set improvement targets:</p>'
                '<ul>'
                '<li>Track your scores across tournaments to identify trends</li>'
                '<li>Compare your average to the tournament\'s overall speaker average</li>'
                '<li>Focus on moving from "average" (75–79) to "good" (80+) by improving rebuttal and argument depth</li>'
                '<li>Ask adjudicators for specific feedback after oral adjs — what would push your speech up 2–3 points?</li>'
                '</ul>'
            ),
        },

        'building-strong-arguments': {
            'status': 'published',
            'reading_time_minutes': 8,
            'summary': 'Learn the fundamentals of argument construction — from assertion to reasoning to evidence — to make your debate speeches more persuasive and structurally sound.',
            'body': (
                '<h2>What Makes an Argument?</h2>'
                '<p>In competitive debate, an "argument" is not just a claim or opinion. It is a structured piece of reasoning that '
                'persuades the judge that your claim is true. Judges consistently reward speakers who build arguments with clear '
                'logic, specific mechanisms, and relevant evidence. Understanding the anatomy of a strong argument is the single '
                'most important skill a debater can develop.</p>'

                '<h2>The ARE Framework</h2>'
                '<p>The most widely used framework for argument construction in parliamentary debate is ARE — Assertion, Reasoning, '
                'Evidence:</p>'
                '<ol>'
                '<li><strong>Assertion:</strong> State your claim clearly and specifically. What exactly are you arguing? '
                'For example: "This policy will reduce income inequality in developing countries."</li>'
                '<li><strong>Reasoning:</strong> Explain <em>why</em> your claim is true. This is the mechanism — the logical chain '
                'that connects your claim to reality. What causal process makes this outcome likely? For example: "Because progressive '
                'taxation redistributes wealth from high earners to public services that disproportionately benefit low-income '
                'households, creating a multiplier effect on social mobility."</li>'
                '<li><strong>Evidence:</strong> Support your reasoning with concrete examples, data, analogies, or historical '
                'precedents. This makes your argument tangible and credible. For example: "The Nordic countries demonstrate this — '
                'Sweden\'s progressive tax system funds universal healthcare and education, contributing to one of the lowest '
                'Gini coefficients globally."</li>'
                '</ol>'

                '<h2>Going Beyond ARE: The AREA Framework</h2>'
                '<p>Top-level debaters extend ARE with an additional step — Analysis, creating the AREA framework:</p>'
                '<ul>'
                '<li><strong>Assertion</strong> — state your claim</li>'
                '<li><strong>Reasoning</strong> — explain the mechanism</li>'
                '<li><strong>Evidence</strong> — provide concrete support</li>'
                '<li><strong>Analysis</strong> — explain why this matters in the context of the debate, and why it should '
                'outweigh opposing arguments</li>'
                '</ul>'
                '<p>The analysis step is what separates good speakers from great ones. It demonstrates that you understand not just '
                'your own argument, but how it fits into the broader debate and why the judge should find it more compelling than '
                'the other side\'s case.</p>'

                '<h2>Common Argument Mistakes</h2>'
                '<p>Even experienced debaters fall into these traps:</p>'

                '<h3>1. Assertion Without Reasoning</h3>'
                '<p>Stating "This policy is bad for the economy" without explaining <em>why</em> or <em>how</em> is not an argument — '
                'it is a bare assertion. Judges will ignore claims that lack reasoning, no matter how confidently they are stated.</p>'

                '<h3>2. Evidence Without Explanation</h3>'
                '<p>Dropping a statistic or country example without explaining how it supports your argument is name-dropping, '
                'not argumentation. Always connect your evidence back to your reasoning: "This matters because..."</p>'

                '<h3>3. Generic Arguments</h3>'
                '<p>Arguments that could apply to almost any motion — like "this violates human rights" or "this is paternalistic" — '
                'without specific analysis of <em>how</em> they apply to the current motion are weak. Judges reward specificity and '
                'reward arguments that are clearly tailored to the motion at hand.</p>'

                '<h3>4. Mechanism-Free Impact Claims</h3>'
                '<p>Claiming "thousands will die" or "the economy will collapse" without explaining the causal mechanism is alarmism, '
                'not argumentation. Always explain the step-by-step process that leads from the policy to the claimed impact.</p>'

                '<h2>Types of Arguments</h2>'
                '<p>Different types of arguments serve different functions in a debate:</p>'
                '<ul>'
                '<li><strong>Principled arguments:</strong> Based on moral or philosophical principles (rights, fairness, autonomy, '
                'justice). Effective when the debate involves value conflicts.</li>'
                '<li><strong>Practical arguments:</strong> Based on real-world outcomes and consequences. Effective when the debate '
                'is about whether a policy would work.</li>'
                '<li><strong>Comparative arguments:</strong> Comparing the status quo with the proposed change, or comparing different '
                'stakeholders\' interests. Effective for weighing competing considerations.</li>'
                '<li><strong>Counter-intuitive arguments:</strong> Arguments that challenge the obvious assumption. Often risky but '
                'highly rewarding when well-supported — they demonstrate sophisticated thinking.</li>'
                '</ul>'

                '<h2>Building Arguments Under Time Pressure</h2>'
                '<p>In impromptu debates, you often have 15–30 minutes to prepare. Here is a practical process:</p>'
                '<ol>'
                '<li><strong>Brainstorm stakeholders:</strong> Who is affected by this motion? List 3–5 groups.</li>'
                '<li><strong>Identify mechanisms:</strong> For each stakeholder, what changes under the motion? What causal chain '
                'leads from the motion to an impact on them?</li>'
                '<li><strong>Select your strongest 2–3 arguments:</strong> Choose arguments with clear mechanisms and available '
                'evidence. Depth beats breadth.</li>'
                '<li><strong>Structure each argument:</strong> Use ARE/AREA. Write a one-sentence assertion for each, then note '
                'the key reasoning points and 1–2 pieces of evidence.</li>'
                '</ol>'

                '<h2>Practice Exercises</h2>'
                '<p>Improve your argument construction with these drills:</p>'
                '<ul>'
                '<li><strong>Motion analysis:</strong> Take any motion from the <a href="/motions-bank/">Motion Bank</a> and '
                'write out 3 arguments for each side using the AREA framework. Time yourself — aim for 15 minutes.</li>'
                '<li><strong>Evidence bank:</strong> Build a personal database of examples, case studies, and data points '
                'organised by topic area (economics, human rights, environment, etc.). Review it regularly.</li>'
                '<li><strong>Argument repair:</strong> Take a weak argument (assertion only) and add reasoning, evidence, '
                'and analysis to make it compelling.</li>'
                '</ul>'
            ),
        },

        # ── Previously DRAFT articles — now expanded and published ──

        'how-to-write-motions': {
            'status': 'published',
            'reading_time_minutes': 8,
            'summary': 'Guidelines for crafting fair, debatable motions — including balance testing, clarity, and avoiding common pitfalls. Essential reading for chief adjudicators and tournament organisers.',
            'body': (
                '<h2>Why Motion Quality Matters</h2>'
                '<p>The quality of motions defines the quality of debates. A well-crafted motion creates engaging, balanced debates '
                'where both sides have strong arguments to make. A poorly crafted motion leads to one-sided debates, confused '
                'definitions, or arguments that miss each other entirely. Chief adjudicators and motion-setting committees carry '
                'enormous responsibility for the tournament experience.</p>'

                '<h2>Anatomy of a Good Motion</h2>'
                '<p>Every strong debate motion shares certain qualities:</p>'
                '<ul>'
                '<li><strong>Balance:</strong> Both sides should have roughly equal ground. If every reasonable person would agree '
                'with one side, the motion is too one-sided.</li>'
                '<li><strong>Clarity:</strong> The motion should be unambiguous. Debaters should not need to spend significant time '
                'defining terms or figuring out what they are debating.</li>'
                '<li><strong>Depth:</strong> The motion should allow for deep, multi-layered analysis — not just surface-level arguments.</li>'
                '<li><strong>Accessibility:</strong> Debaters with general knowledge should be able to engage meaningfully, even if '
                'the topic is specialised. Avoid motions that require niche expertise.</li>'
                '<li><strong>Relevance:</strong> While historical or philosophical motions have their place, motions connected to '
                'current events or enduring social questions tend to generate more engaging debates.</li>'
                '</ul>'

                '<h2>Types of Motions</h2>'
                '<p>Understanding motion types helps you craft appropriate motions for different rounds:</p>'
                '<ul>'
                '<li><strong>"This House Would" (THW):</strong> Policy motions where the government proposes a specific action. '
                'These require clear, implementable proposals. Example: "THW ban political advertising on social media."</li>'
                '<li><strong>"This House Believes That" (THBT):</strong> Value or analysis motions where teams debate whether '
                'something is true or desirable. Example: "THBT liberal democracies should prioritise economic equality over '
                'economic growth."</li>'
                '<li><strong>"This House Supports" (THS):</strong> Endorsement motions where the government argues in favour of '
                'a position, movement, or trend. Example: "THS the rise of remote work."</li>'
                '<li><strong>"This House Regrets" (THR):</strong> Backward-looking motions that evaluate whether something that '
                'happened was net positive or negative. Example: "THR the development of nuclear energy."</li>'
                '</ul>'

                '<h2>Testing for Balance</h2>'
                '<p>Before finalising a motion, use these balance-testing techniques:</p>'
                '<ol>'
                '<li><strong>Three-argument test:</strong> Can you quickly think of at least three strong, distinct arguments '
                'for each side? If one side struggles to reach three, the motion may be unbalanced.</li>'
                '<li><strong>Devil\'s advocate test:</strong> Argue the side you personally disagree with. If you find it very '
                'difficult to construct a compelling case, the motion is likely problematic.</li>'
                '<li><strong>Crowd-source test:</strong> Share the motion with experienced debaters and ask which side they would '
                'prefer to be on. If there is strong consensus for one side, revisit the wording.</li>'
                '<li><strong>Stakeholder analysis:</strong> List the key stakeholders affected by the motion. Does each side have '
                'stakeholders whose interests support their case?</li>'
                '</ol>'

                '<h2>Common Motion-Setting Mistakes</h2>'
                '<p>Avoid these pitfalls that lead to poor debates:</p>'
                '<ul>'
                '<li><strong>Truism motions:</strong> Motions where the proposition is obviously true ("THBT education is important"). '
                'No reasonable opposition case exists.</li>'
                '<li><strong>Squirrelable motions:</strong> Motions where vague wording allows the government to "squirrel" — '
                'defining the motion in an unexpected way that leaves the opposition unable to prepare.</li>'
                '<li><strong>Knowledge-gated motions:</strong> Motions requiring specific technical or regional knowledge that '
                'creates an unfair advantage for some debaters.</li>'
                '<li><strong>Over-specified motions:</strong> Motions with so many details that they constrain the debate and '
                'leave no room for teams to be creative. Example: "THW impose a 25% tariff on Chinese semiconductors entering '
                'the EU, with exemptions for medical devices, phased in over 3 years."</li>'
                '<li><strong>Actor-absent motions:</strong> Policy motions that do not specify who is implementing the policy, '
                'leading to confusion about context and scope.</li>'
                '</ul>'

                '<h2>Crafting Infoslides</h2>'
                '<p>For motions that require context, an infoslide provides necessary background information. Good infoslides:</p>'
                '<ul>'
                '<li>Are factual and objective — they should not argue for either side</li>'
                '<li>Provide only the information needed to understand and debate the motion</li>'
                '<li>Are concise — typically 3–5 sentences maximum</li>'
                '<li>Define any technical terms or context-specific concepts</li>'
                '</ul>'

                '<h2>Motion Sets for Tournaments</h2>'
                '<p>When setting motions for a full tournament, consider the overall balance of your motion set:</p>'
                '<ul>'
                '<li>Mix topic areas — do not set five rounds of political motions</li>'
                '<li>Include both policy and value motions</li>'
                '<li>Progress in complexity — earlier rounds can be more accessible, with later rounds demanding deeper analysis</li>'
                '<li>Consider the audience — a school tournament should have different motions than an international championship</li>'
                '</ul>'
                '<p>Use the <a href="/motions-bank/">NekoTab Motion Bank</a> to research what motions have been used at similar '
                'tournaments, and the <a href="/motions-bank/doctor/">Motion Doctor</a> to test your motions for balance and depth.</p>'
            ),
        },

        'organising-first-tournament': {
            'status': 'published',
            'reading_time_minutes': 10,
            'summary': 'A step-by-step checklist for hosting a competitive debate tournament — from venue booking to tab release. Everything a first-time tournament director needs to know.',
            'body': (
                '<h2>Planning Your Tournament</h2>'
                '<p>Hosting a debate tournament is a rewarding but complex undertaking. Whether you are organising a small internal '
                'club competition or a regional intervarsity event, careful planning is the key to a smooth experience for participants, '
                'judges, and organisers alike.</p>'

                '<h2>Timeline and Milestones</h2>'
                '<p>Start planning at least 2–3 months before the tournament date. Here is a recommended timeline:</p>'

                '<h3>3 Months Before</h3>'
                '<ul>'
                '<li>Fix the date and debate format (BP, Australs, WSDC)</li>'
                '<li>Book the venue — ensure enough rooms for all debates plus a common area</li>'
                '<li>Assemble your organising committee: tournament director, chief adjudicator, tab director, logistics lead</li>'
                '<li>Set a budget covering venue, food, prizes, printing, and any travel subsidies</li>'
                '<li>Open registration — create a form collecting team names, speaker names, institution, and dietary requirements</li>'
                '</ul>'

                '<h3>1–2 Months Before</h3>'
                '<ul>'
                '<li>Confirm the chief adjudicator and begin motion-setting</li>'
                '<li>Recruit independent adjudicators — aim for at least 1 judge per 2 teams</li>'
                '<li>Set up NekoTab: create your tournament, configure the format preset, and import participants</li>'
                '<li>Plan the schedule: registration time, number of preliminary rounds, break format, and final</li>'
                '<li>Organise catering, signage, and any social events</li>'
                '</ul>'

                '<h3>1 Week Before</h3>'
                '<ul>'
                '<li>Finalise motions and prepare infoslides</li>'
                '<li>Enter all teams, speakers, adjudicators, and venues into NekoTab</li>'
                '<li>Configure institutional conflicts, adjudicator scores, and feedback forms</li>'
                '<li>Prepare printed materials: venue maps, schedules, feedback ballots (if using paper)</li>'
                '<li>Brief your team on day-of logistics: who runs registration, who manages timekeeping, who handles tech</li>'
                '</ul>'

                '<h2>Day-of Operations</h2>'
                '<p>The tournament day is about execution. Here is a round-by-round workflow:</p>'

                '<h3>Registration</h3>'
                '<p>Allow 30–60 minutes for check-in. Confirm team rosters, distribute venue maps, and brief participants on '
                'the schedule and rules. Use NekoTab\'s check-in feature to track who has arrived.</p>'

                '<h3>Each Round</h3>'
                '<ol>'
                '<li><strong>Generate the draw:</strong> Use NekoTab to auto-generate the draw with power-pairing (after Round 1, '
                'which uses random allocation).</li>'
                '<li><strong>Allocate judges:</strong> Use NekoTab\'s allocation tools to assign panels based on judge scores '
                'and conflicts.</li>'
                '<li><strong>Release the draw:</strong> Publish to the public site or display in the common area.</li>'
                '<li><strong>Motion release:</strong> Announce the motion according to your format\'s procedure.</li>'
                '<li><strong>Prep time:</strong> Allow the standard preparation time (15 minutes for BP, 30 minutes for impromptu WSDC).</li>'
                '<li><strong>Debates:</strong> Ensure timekeepers are in each room. Monitor for any issues.</li>'
                '<li><strong>Ballot collection:</strong> Collect digital or paper ballots. Enter results into NekoTab.</li>'
                '<li><strong>Feedback:</strong> Collect adjudicator feedback after each round.</li>'
                '</ol>'

                '<h3>Break and Finals</h3>'
                '<p>After all preliminary rounds:</p>'
                '<ul>'
                '<li>Generate the break using NekoTab\'s break calculation tools</li>'
                '<li>Announce the break publicly</li>'
                '<li>Generate elimination round draws</li>'
                '<li>Adjudicate finals with your strongest panel</li>'
                '</ul>'

                '<h3>Closing Ceremony</h3>'
                '<p>Announce all results: team rankings, speaker prizes, best adjudicator, and any special awards. '
                'Publish final results to the NekoTab public site for permanent archival.</p>'

                '<h2>Budgeting</h2>'
                '<p>Common tournament expenses include:</p>'
                '<ul>'
                '<li><strong>Venue hire:</strong> Often the largest cost, unless your institution provides rooms for free</li>'
                '<li><strong>Catering:</strong> Budget for at least lunch and refreshments; multi-day tournaments need dinner too</li>'
                '<li><strong>Prizes:</strong> Trophies, certificates, or other awards</li>'
                '<li><strong>Printing:</strong> If using paper ballots, schedules, or name tags</li>'
                '<li><strong>Judge travel:</strong> If bringing external chief adjudicators or independent judges</li>'
                '</ul>'
                '<p>Registration fees from participating teams typically cover most or all of these costs.</p>'

                '<h2>Using NekoTab for Your Tournament</h2>'
                '<p>NekoTab simplifies tournament administration significantly:</p>'
                '<ul>'
                '<li><a href="/create/">Create a tournament</a> in under 2 minutes with format presets</li>'
                '<li>Import teams, speakers, and judges via CSV</li>'
                '<li>Auto-generate power-paired draws with side balancing</li>'
                '<li>Manage judge allocations with conflict detection</li>'
                '<li>Collect digital ballots with validation</li>'
                '<li>Publish results, draws, and motions on a public site</li>'
                '<li>Generate breaks and elimination rounds automatically</li>'
                '</ul>'
                '<p>Read the <a href="https://tabbycat.readthedocs.io/" target="_blank" rel="noopener">documentation</a> '
                'for a complete guide to NekoTab\'s features.</p>'
            ),
        },

        'points-of-information-guide': {
            'status': 'published',
            'reading_time_minutes': 7,
            'summary': 'Master the art of giving and responding to Points of Information in parliamentary debate. Covers timing, strategy, etiquette, and common mistakes.',
            'body': (
                '<h2>What Is a Point of Information?</h2>'
                '<p>A Point of Information (POI) is a brief interjection offered by a member of an opposing team during a speech '
                'in parliamentary debate. POIs are a fundamental feature of British Parliamentary, Australs, and WSDC formats. '
                'They allow opposing teams to challenge the speaker, ask questions, or make short counter-points — keeping the '
                'debate interactive and testing speakers\' ability to think on their feet.</p>'

                '<h2>When Can You Offer POIs?</h2>'
                '<p>POIs may only be offered during the "unprotected" portion of a speech:</p>'
                '<ul>'
                '<li><strong>BP (7-minute speeches):</strong> POIs are allowed between 1:00 and 6:00 — the first and last minutes are protected</li>'
                '<li><strong>Australs (7-8 minute speeches):</strong> Same principle — first and last minute protected</li>'
                '<li><strong>WSDC (8-minute speeches):</strong> POIs allowed between 1:00 and 7:00</li>'
                '</ul>'
                '<p>A single knock (or bell) signals the end of the first protected minute, and a double knock signals the start '
                'of the final protected minute. Some tournaments use digital timers that display "POI" when POIs are permitted.</p>'

                '<h2>How to Offer a POI</h2>'
                '<p>To offer a POI, stand up from your seat and say "Point of information" or simply "On that point." '
                'Keep your hand raised until the speaker accepts or declines. Key etiquette:</p>'
                '<ul>'
                '<li>Stand briefly and confidently — do not hover for extended periods</li>'
                '<li>If the speaker says "No, thank you" or waves you down, sit immediately</li>'
                '<li>Do not interrupt the speaker if they have not acknowledged you</li>'
                '<li>Do not stand up repeatedly in quick succession (known as "barracking") — it is considered disruptive</li>'
                '<li>Both speakers from your team can offer POIs, but coordinate — do not both stand at the same time</li>'
                '</ul>'

                '<h2>Crafting Effective POIs</h2>'
                '<p>A good POI is brief (under 15 seconds), targeted, and strategically timed. The best POIs achieve one of these goals:</p>'

                '<h3>1. Expose a Contradiction</h3>'
                '<p>"Your first speaker said X, but you are now arguing Y — which is your team\'s position?"</p>'
                '<p>This forces the speaker to either reconcile the contradiction or lose credibility.</p>'

                '<h3>2. Demand a Mechanism</h3>'
                '<p>"How exactly would this policy be enforced in practice?"</p>'
                '<p>Effective against teams that make large claims without explaining implementation.</p>'

                '<h3>3. Highlight a Missing Stakeholder</h3>'
                '<p>"What about the impact on [group your opponents haven\'t considered]?"</p>'
                '<p>This introduces a perspective the speaker must address or appear to have an incomplete analysis.</p>'

                '<h3>4. Set Up Your Own Argument</h3>'
                '<p>"If you accept that [small concession], then by your own logic [devastating conclusion]."</p>'
                '<p>This is advanced — you use the POI to create a logical trap that your team can exploit later.</p>'

                '<h2>Responding to POIs</h2>'
                '<p>How you handle POIs affects your speaker score and team ranking. Guidelines for speakers:</p>'
                '<ul>'
                '<li><strong>Accept at least 1–2 POIs per speech:</strong> Refusing all POIs is penalised by judges. '
                'It suggests you cannot defend your arguments under challenge.</li>'
                '<li><strong>Accept strategically:</strong> Take POIs when you are on strong ground — after making a point '
                'you are confident about, not in the middle of a complex explanation.</li>'
                '<li><strong>Respond concisely:</strong> Acknowledge the point, give a brief answer, and return to your '
                'argument. Do not let the POI derail your speech structure.</li>'
                '<li><strong>Use POIs to your advantage:</strong> If an opponent\'s question is weak, point out why: '
                '"Thank you — that actually supports our case because..."</li>'
                '<li><strong>Decline politely:</strong> A simple "No, thank you" is sufficient. Do not respond aggressively '
                'to offers.</li>'
                '</ul>'

                '<h2>Common POI Mistakes</h2>'
                '<ul>'
                '<li><strong>Speeches disguised as questions:</strong> POIs that run for 30+ seconds are lectures, not points. '
                'The speaker should cut you off after 15 seconds.</li>'
                '<li><strong>Unclear or convoluted POIs:</strong> If the speaker and the audience cannot understand your point, '
                'it has no impact. Keep it simple and direct.</li>'
                '<li><strong>Offering too many:</strong> Standing up every 30 seconds is barracking. Offer 3–5 POIs per speech '
                'and choose your moments carefully.</li>'
                '<li><strong>Offering too few:</strong> Never standing up suggests disengagement or inability to challenge the '
                'other side. Judges notice.</li>'
                '<li><strong>Taking POIs at bad times:</strong> Accepting a POI when you have 30 seconds left and have not '
                'finished your argument is a strategic error.</li>'
                '</ul>'

                '<h2>POI Strategy by Position</h2>'
                '<p>Different speaker positions should approach POIs differently:</p>'
                '<ul>'
                '<li><strong>Opening speakers:</strong> Use POIs to establish key challenges early. Set the terms of clash.</li>'
                '<li><strong>Closing speakers:</strong> Use POIs to test whether your extension is needed — if the opening '
                'half\'s case has a gap, your POI can highlight it.</li>'
                '<li><strong>Whip/reply speakers:</strong> You cannot offer POIs during reply speeches. Focus on using '
                'earlier POIs as evidence in your summary.</li>'
                '</ul>'
            ),
        },

        'chief-adjudicator-role': {
            'status': 'published',
            'reading_time_minutes': 8,
            'summary': 'What chief adjudicators do, how they set motions, manage panels, and ensure fair adjudication across a tournament. A guide for aspiring CAs.',
            'body': (
                '<h2>What Does a Chief Adjudicator Do?</h2>'
                '<p>The Chief Adjudicator (CA) is responsible for the quality and fairness of adjudication throughout a debate '
                'tournament. While the tab director manages logistics and the tournament director handles operations, the CA '
                'oversees everything related to the substance of the debates: motions, judge training, panel allocation, and '
                'adjudication standards.</p>'

                '<h2>Core Responsibilities</h2>'

                '<h3>1. Motion Setting</h3>'
                '<p>The CA leads the process of creating or selecting motions for every round. This involves:</p>'
                '<ul>'
                '<li>Drafting an initial set of candidate motions across different topic areas</li>'
                '<li>Testing motions with a motion committee for balance, clarity, and depth</li>'
                '<li>Selecting the final motion set that provides variety and appropriate progression in difficulty</li>'
                '<li>Writing infoslides where necessary</li>'
                '<li>Preparing backup motions in case of unforeseen issues</li>'
                '</ul>'
                '<p>CAs typically start working on motions weeks before the tournament, refining them through multiple rounds of review.</p>'

                '<h3>2. Adjudicator Briefing</h3>'
                '<p>Before the tournament begins, the CA delivers a judging briefing that covers:</p>'
                '<ul>'
                '<li>The tournament\'s specific rules and format variations</li>'
                '<li>Speaker score scale guidelines and expectations</li>'
                '<li>How to handle points of order, POIs, and protected time</li>'
                '<li>The process for submitting ballots and feedback</li>'
                '<li>The standard for oral adjudications — timing, structure, and tone</li>'
                '<li>Specific guidance for any format-specific judging challenges</li>'
                '</ul>'

                '<h3>3. Panel Allocation</h3>'
                '<p>The CA, often working with a deputy chief adjudicator (DCA) team, allocates adjudicator panels for each round. '
                'Good panel allocation requires:</p>'
                '<ul>'
                '<li>Matching judge strength to debate importance — the strongest panels go to the strongest debates</li>'
                '<li>Ensuring institutional conflict rules are respected — no judge from the same institution as a competing team</li>'
                '<li>Balancing experience across panels — mixing experienced chairs with developing wing judges</li>'
                '<li>Rotating judges — avoiding the same judge seeing the same team repeatedly</li>'
                '<li>Using feedback from previous rounds to adjust judge assignments dynamically</li>'
                '</ul>'

                '<h3>4. Adjudicator Development</h3>'
                '<p>Good CAs invest in developing the judging pool throughout the tournament:</p>'
                '<ul>'
                '<li>Providing individual feedback to judges after reviewing their ballots and feedback scores</li>'
                '<li>Shadowing judges in rooms to observe their deliberations and oral adjudications</li>'
                '<li>"Breaking" (promoting) wing judges to chair positions as they demonstrate competence</li>'
                '<li>Addressing problematic judging patterns — such as score compression, biases, or poorly reasoned decisions</li>'
                '</ul>'

                '<h3>5. Dispute Resolution</h3>'
                '<p>When adjudication disputes arise — a team believes a decision was clearly incorrect, or there are concerns about '
                'judge behaviour — the CA is the ultimate arbiter. They must:</p>'
                '<ul>'
                '<li>Listen to concerns respectfully and thoroughly</li>'
                '<li>Review the relevant ballots and, if necessary, speak with the judges involved</li>'
                '<li>Make fair decisions based on established tournament rules</li>'
                '<li>Communicate decisions clearly, explaining the reasoning</li>'
                '</ul>'

                '<h2>Working with the CA Team</h2>'
                '<p>At larger tournaments, the CA works with a team of Deputy Chief Adjudicators (DCAs). Effective CA teams:</p>'
                '<ul>'
                '<li>Divide responsibilities clearly — e.g., one DCA handles panel allocation, another handles feedback review</li>'
                '<li>Communicate constantly during the tournament — a shared group chat or in-person check-ins between rounds</li>'
                '<li>Present a unified front on adjudication standards — DCAs should not contradict the CA\'s briefing</li>'
                '</ul>'

                '<h2>Preparing to Be a CA</h2>'
                '<p>If you aspire to be a chief adjudicator, here is a development pathway:</p>'
                '<ol>'
                '<li><strong>Judge extensively:</strong> You need deep experience as both a wing and chair adjudicator across many '
                'tournaments before taking on the CA role.</li>'
                '<li><strong>Join CA panels:</strong> Serve as a DCA first to learn the operational aspects — panel allocation, '
                'motion review, and feedback management.</li>'
                '<li><strong>Study motion-setting:</strong> Analyze motion sets from major tournaments. Read post-tournament '
                'reports that discuss motion quality.</li>'
                '<li><strong>Seek feedback:</strong> Ask experienced CAs for mentorship and feedback on your judging and '
                'adjudication leadership.</li>'
                '</ol>'

                '<h2>Using NekoTab as a CA</h2>'
                '<p>NekoTab provides tools that make the CA\'s job significantly easier:</p>'
                '<ul>'
                '<li><strong>Adjudicator allocation:</strong> Smart panel assignment with conflict detection and scoring</li>'
                '<li><strong>Feedback aggregation:</strong> Review adjudicator feedback scores across rounds to identify trends</li>'
                '<li><strong>Motion management:</strong> Store and manage motions for each round</li>'
                '<li><strong>Real-time standings:</strong> Monitor team and speaker rankings to identify potential issues</li>'
                '</ul>'
            ),
        },

        'using-nekotab-guide': {
            'status': 'published',
            'reading_time_minutes': 8,
            'summary': 'A walkthrough of NekoTab features — setting up a tournament, importing data, running rounds, and publishing results. The complete guide to using NekoTab for tournament tabulation.',
            'body': (
                '<h2>Getting Started</h2>'
                '<p>NekoTab is a modern debate tournament tabulation platform that handles everything from team registration to final '
                'results. Whether you are running a small club competition or a national championship, this guide walks you through '
                'the key features and workflows.</p>'

                '<h2>Creating Your Tournament</h2>'
                '<ol>'
                '<li><strong>Sign up or log in:</strong> Create an account at nekotab.app. No email verification is required — '
                'just a username and password.</li>'
                '<li><strong>Click "Create Tournament":</strong> From the homepage or the top navigation bar.</li>'
                '<li><strong>Configure basics:</strong> Enter a tournament name, short name (used in URLs), and select a format '
                'preset (BP, Australs, WSDC, or custom).</li>'
                '<li><strong>Set the number of preliminary rounds:</strong> You can always add more rounds later.</li>'
                '<li><strong>Click "Create":</strong> Your tournament is ready. You are taken to the admin panel.</li>'
                '</ol>'

                '<h2>Importing Participants</h2>'
                '<p>NekoTab supports bulk importing of teams, speakers, adjudicators, and venues via CSV files:</p>'

                '<h3>Teams and Speakers</h3>'
                '<ol>'
                '<li>Go to Participants → Import Teams in the admin panel</li>'
                '<li>Upload a CSV file with columns: team name, institution, speaker 1 name, speaker 2 name (and speaker 3 for Australs/WSDC)</li>'
                '<li>Review the preview and confirm the import</li>'
                '</ol>'

                '<h3>Adjudicators</h3>'
                '<ol>'
                '<li>Go to Participants → Import Adjudicators</li>'
                '<li>Upload a CSV with columns: name, institution, base score (a number representing judging ability)</li>'
                '<li>Set any institutional conflicts — NekoTab will prevent judges from being allocated to debates involving their institution</li>'
                '</ol>'

                '<h3>Venues</h3>'
                '<ol>'
                '<li>Go to Venues → Import Venues</li>'
                '<li>Upload a CSV with room names and optional priority numbers</li>'
                '<li>Higher-priority venues are assigned to more important debates</li>'
                '</ol>'

                '<h2>Running a Round</h2>'
                '<p>The round workflow in NekoTab follows a clear sequence:</p>'

                '<h3>Step 1: Generate the Draw</h3>'
                '<p>From the admin panel, navigate to the current round and click "Generate Draw." NekoTab will create a power-paired '
                'draw (or random draw for Round 1) that respects side allocation, pullup rules, and venue priority.</p>'
                '<p>Review the draw and make any manual adjustments if needed.</p>'

                '<h3>Step 2: Allocate Adjudicators</h3>'
                '<p>Navigate to the allocation page. NekoTab provides an auto-allocator that assigns judges based on their score, '
                'conflicts, and history. You can also drag-and-drop to manually adjust panels.</p>'

                '<h3>Step 3: Release the Draw</h3>'
                '<p>Click "Confirm" to finalise the draw, then "Release" to make it visible on the public site. Teams will see '
                'their room, opponents, and panel.</p>'

                '<h3>Step 4: Announce the Motion</h3>'
                '<p>Enter the round\'s motion in NekoTab. Optionally release it to the public site.</p>'

                '<h3>Step 5: Collect Results</h3>'
                '<p>After the debate, enter results through one of two methods:</p>'
                '<ul>'
                '<li><strong>Admin entry:</strong> Organisers enter results in the admin panel</li>'
                '<li><strong>Public/private ballot submission:</strong> Enable online ballot submission for adjudicators using '
                'private URLs sent via email or QR code</li>'
                '</ul>'
                '<p>NekoTab validates all results — checking for required speaker scores, consistent rankings, and confirmed '
                'adjudicator identities.</p>'

                '<h3>Step 6: Confirm and Release Results</h3>'
                '<p>Once all results are entered and validated, confirm the round. Results are automatically reflected in '
                'standings, speaker rankings, and the public site.</p>'

                '<h2>Standings and Breaks</h2>'
                '<p>NekoTab calculates team and speaker standings in real-time using configurable metrics:</p>'
                '<ul>'
                '<li><strong>Team standings:</strong> Based on wins (or team points in BP) with configurable tie-breaking '
                'by speaker scores, margins, or draw strength</li>'
                '<li><strong>Speaker standings:</strong> Ranked by total speaker points across rounds</li>'
                '<li><strong>Break calculation:</strong> Configure break categories (open break, novice break, ESL break, etc.) '
                'with automatic qualification based on standings</li>'
                '</ul>'

                '<h2>Public Site</h2>'
                '<p>Every tournament on NekoTab has a public-facing site. Configure what is visible:</p>'
                '<ul>'
                '<li>Draws and motions (released per-round)</li>'
                '<li>Results and standings (immediate or delayed release)</li>'
                '<li>Team and speaker details</li>'
                '<li>Break announcements</li>'
                '</ul>'
                '<p>The public site is mobile-responsive and can be shared with participants via a simple URL.</p>'

                '<h2>Advanced Features</h2>'
                '<ul>'
                '<li><strong>Check-ins:</strong> QR code-based attendance tracking for teams and judges</li>'
                '<li><strong>Feedback:</strong> Collect and review adjudicator feedback per round</li>'
                '<li><strong>Notifications:</strong> Send draw releases and announcements via email</li>'
                '<li><strong>Preformed panels:</strong> Pre-arrange judge panels before draws are released</li>'
                '<li><strong>Multiple break categories:</strong> Open, novice, ESL, and custom categories with separate breaks</li>'
                '</ul>'

                '<h2>Need Help?</h2>'
                '<p>For detailed documentation, visit the <a href="https://tabbycat.readthedocs.io/" target="_blank" rel="noopener">'
                'Tabbycat documentation</a>. For support, <a href="/contact/">contact us</a> and we will help you get set up.</p>'
            ),
        },

        'reply-speeches-guide': {
            'status': 'published',
            'reading_time_minutes': 6,
            'summary': 'How to deliver an effective reply speech — structuring your summary, framing the debate, and maximizing impact. Essential for Australs and WSDC debaters.',
            'body': (
                '<h2>What Is a Reply Speech?</h2>'
                '<p>The reply speech is a shorter summary speech delivered at the end of a debate in Australs and WSDC formats. '
                'Unlike substantive speeches, the reply speech does not introduce new arguments. Instead, it provides a "bird\'s-eye '
                'view" of the debate, identifying the key issues and explaining why your team has won them. It is the last chance '
                'to shape how the judges see the debate.</p>'

                '<h2>Who Delivers the Reply?</h2>'
                '<p>In most formats, the reply speech is delivered by either the 1st or 2nd speaker on each team (not the 3rd). '
                'The order is reversed — the opposition replies first, and the proposition (or affirmative) gets the final word. '
                'Reply speeches are typically 4–5 minutes, compared to 7–8 minutes for substantive speeches.</p>'

                '<h2>Structure of a Reply Speech</h2>'
                '<p>An effective reply speech follows a specific structure that is quite different from a substantive speech:</p>'

                '<h3>1. Opening Frame (30 seconds)</h3>'
                '<p>Begin with a clear statement of the debate\'s central question and your team\'s answer to it. This should be a '
                'one-sentence thesis that captures the essence of your case. For example: "This debate comes down to whether the '
                'state has a greater obligation to protect individual liberty or collective welfare — and we have shown convincingly '
                'that liberty must take priority."</p>'

                '<h3>2. Issue Identification (1 minute)</h3>'
                '<p>Identify the 2–3 most important clashes or issues in the debate. These are the fundamental questions that '
                'the debate revolved around. Explicitly name them: "There were three key clashes in this debate: first, whether '
                'the policy would work in practice; second, whether it is principled; and third, who bears the burden of proof."</p>'

                '<h3>3. Clash Analysis (2–3 minutes)</h3>'
                '<p>For each key issue, explain:</p>'
                '<ul>'
                '<li>What your team argued</li>'
                '<li>What the opposing team argued</li>'
                '<li>Why your team\'s position is more persuasive</li>'
                '</ul>'
                '<p>This is the core of the reply speech. You must be fair in characterising the opposing team\'s arguments — '
                'straw-manning them will damage your credibility — but then demonstrate why your team\'s analysis was superior.</p>'

                '<h3>4. Closing Statement (30 seconds)</h3>'
                '<p>End with a concise, powerful summary of why your team won the debate overall. Bring it back to the big picture '
                'and leave the judges with a clear narrative.</p>'

                '<h2>What Makes a Great Reply Speech</h2>'
                '<p>The best reply speeches share these characteristics:</p>'
                '<ul>'
                '<li><strong>Objectivity:</strong> Great reply speakers sound like fair analysts rather than partisan advocates. '
                'They acknowledge the other side\'s arguments before explaining why their team\'s are stronger.</li>'
                '<li><strong>Selectivity:</strong> You cannot cover everything in 4 minutes. Choose the 2–3 issues that matter '
                'most — the clashes that, if won, should determine the judge\'s decision.</li>'
                '<li><strong>Synthesis:</strong> Do not simply repeat what your speakers said. Synthesise — show how your team\'s '
                'arguments work together to form a coherent, compelling case.</li>'
                '<li><strong>New framing (not new arguments):</strong> You can offer a new way of looking at the debate — a '
                'framework for weighing the issues — as long as you are not introducing new substantive material.</li>'
                '</ul>'

                '<h2>Common Reply Speech Mistakes</h2>'
                '<ul>'
                '<li><strong>Introducing new arguments:</strong> This is the cardinal sin of reply speeches. New arguments will '
                'be struck by judges, and you will lose credibility.</li>'
                '<li><strong>Rehashing every argument:</strong> A reply speech is not a summary of every point made. It is a '
                'strategic overview of the most important issues.</li>'
                '<li><strong>Ignoring the opposition:</strong> If you do not address the best opposing arguments, judges will '
                'assume you could not respond to them.</li>'
                '<li><strong>Poor time management:</strong> Spending 3 minutes on the first issue and 30 seconds on the rest '
                'leaves an unbalanced impression of the debate.</li>'
                '<li><strong>Reading off notes:</strong> Reply speeches should feel dynamic and responsive to the actual debate '
                'that occurred. Reading a pre-prepared speech sounds disengaged.</li>'
                '</ul>'

                '<h2>Preparing the Reply During the Debate</h2>'
                '<p>Since the reply speaker is either the 1st or 2nd speaker, they have already delivered a substantive speech and '
                'must prepare their reply while listening to the remaining speeches. Practical tips:</p>'
                '<ul>'
                '<li>Take a separate set of notes specifically for the reply speech — identify key clashes as they emerge</li>'
                '<li>After the 3rd speakers finish, you have a few minutes to outline your reply structure</li>'
                '<li>Coordinate with your team — your 3rd speaker can signal which issues to emphasise in the reply</li>'
                '<li>Have a "reply speech template" in your head: opening frame → 2–3 issues → closing</li>'
                '</ul>'

                '<h2>Practice Drills</h2>'
                '<p>To improve your reply speeches:</p>'
                '<ul>'
                '<li><strong>Watch and reply:</strong> Watch a recorded debate and deliver a 4-minute reply speech for one side. '
                'Compare your reply to the actual one (if available).</li>'
                '<li><strong>Speed summaries:</strong> After any practice debate, give an impromptu 2-minute summary of the key '
                'issues and why one side won. This builds the analytical muscles needed for replies.</li>'
                '<li><strong>Framing exercises:</strong> Take a completed debate and try framing it from three different angles — '
                'which framing makes your side sound strongest?</li>'
                '</ul>'
            ),
        },
    }

    for slug, data in updates.items():
        try:
            article = Article.objects.get(slug=slug)
            for field, value in data.items():
                setattr(article, field, value)
            article.save()
        except Article.DoesNotExist:
            pass  # Skip if article was manually deleted


def reverse_expand(apps, schema_editor):
    # No reverse — the original seed migration handles base content
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0002_seed_content'),
    ]

    operations = [
        migrations.RunPython(expand_articles, reverse_expand),
    ]
