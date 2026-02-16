"""
Motion Doctor — 4-Prompt AI Pipeline
=====================================
Prompt A: Motion Profiler (classifier)
Prompt B: Retrieval-conditioned Planner
Prompt C: Report Generator
Prompt D: Validator / Repair
"""

import json
import logging
import time
from os import environ

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt A — Motion Profiler (JSON only)
# =============================================================================

PROMPT_A_SYSTEM = """You are a debate adjudication core member and motion classifier.
You analyze debate motions and produce a structured JSON profile.
Output valid JSON only — no markdown, no commentary, no code fences."""

PROMPT_A_USER = """Analyze this debate motion and produce a structured profile.

Motion: "{motion_text}"
{infoslide_section}
Format: {format}

Produce a JSON object with EXACTLY these keys:
{{
  "format": "{format}",
  "motion_type": "<policy|value|actor|regret|comparative|factual|unclear>",
  "domain_primary": "<the primary domain: bioethics|ai|econ|war|identity|environment|governance|education|health|technology|human_rights|international_relations|criminal_justice|culture|media|religion|philosophy|other>",
  "domain_secondary": ["<list of secondary domains>"],
  "actor": "<who acts, or empty string if none>",
  "action": "<what they do, or empty string>",
  "object": "<what's acted upon, or empty string>",
  "scope": {{
    "geography": "<global|regional|national|local|unspecified>",
    "timeframe": "<immediate|gradual|retrospective|unspecified>",
    "subjects": "<who is affected>",
    "exceptions": ["<any explicit exceptions or 'none_specified'>"]
  }},
  "requires_model": <true if Government needs a concrete policy model, false otherwise>,
  "ambiguity_flags": ["<list specific ambiguities in the motion wording>"],
  "keywords": ["<5-10 domain-specific keywords relevant to this motion>"],
  "confidence": <0.0 to 1.0 — how confident you are in this classification>
}}

RULES:
- If the motion contains undefined or made-up terms, set motion_type to "unclear" and list the term in ambiguity_flags.
- Be specific to THIS motion — do not give generic domains.
- confidence should be lower if the motion is ambiguous or unusual.
- Output ONLY the JSON object, nothing else."""


# =============================================================================
# Prompt B — Retrieval-conditioned Planner
# =============================================================================

PROMPT_B_SYSTEM = """You are a senior debate coach planning a comprehensive motion analysis.
You receive a motion profile and relevant archetypes. Output valid JSON only."""

PROMPT_B_USER = """Plan a comprehensive analysis for this debate motion.

Motion: "{motion_text}"
{infoslide_section}
Format: {format}

MOTION PROFILE:
{profile_json}

MATCHING ARCHETYPES:
{archetypes_json}

SIMILAR PAST MOTIONS:
{similar_motions}

Produce a JSON plan with EXACTLY these keys:
{{
  "clash_axes_to_cover": [
    {{"axis": "<specific clash axis>", "priority": "<high|medium|low>", "source": "<archetype name or 'novel'>"}}
  ],
  "stakeholders_to_analyze": [
    {{"group": "<stakeholder name>", "relevance": "<why they matter for THIS motion>"}}
  ],
  "model_needed": <true|false>,
  "model_guidance": "<what kind of model to suggest, or null>",
  "interpretations_to_offer": [
    {{"reading": "<description of one fair interpretation>", "is_standard": <true|false>}}
  ],
  "things_to_avoid": [
    "<specific pitfall for THIS motion>"
  ],
  "definition_risks": [
    "<specific definition trap for THIS motion>"
  ],
  "weighing_approach": "<how judges should evaluate THIS debate>",
  "extension_strategy": "<what closing teams should focus on>",
  "ambiguity_notes": "<what ambiguity to acknowledge, or null>"
}}

RULES:
- Every item must reference specific entities/concepts from the motion, not generic debate advice.
- Use the archetypes as starting points but ADAPT to this specific motion.
- If the motion is unclear, say so in ambiguity_notes.
- Output ONLY the JSON object."""


# =============================================================================
# Prompt C — Report Generator (JSON only)
# =============================================================================

PROMPT_C_SYSTEM = """You are an elite debate coach generating a Motion Doctor report.
You produce coaching-grade, motion-specific analysis in strict JSON format.
Every claim, argument, and suggestion must reference specific entities from the motion.
Output valid JSON only — no markdown, no commentary."""

PROMPT_C_USER = """Generate a complete Motion Doctor report for this debate motion.

Motion: "{motion_text}"
{infoslide_section}
Format: {format}

ANALYSIS PLAN:
{plan_json}

ARCHETYPE DATA:
{archetypes_json}

Produce a JSON report with EXACTLY this structure:
{{
  "interpretations": [
    {{
      "title": "<short label>",
      "definition": "<how this reading defines key terms>",
      "fairness_notes": "<is this reading fair? does it preserve both sides' ground?>"
    }}
  ],
  "clash_areas": [
    {{
      "axis": "<specific clash axis name>",
      "gov_claim": "<what gov argues on this axis, specific to motion>",
      "opp_claim": "<what opp argues on this axis, specific to motion>"
    }}
  ],
  "hidden_assumptions": [
    "<specific assumption embedded in THIS motion>"
  ],
  "definition_traps": [
    {{
      "trap": "<specific squirrel or unfair definition>",
      "why_bad": "<why it kills the debate>",
      "fair_line": "<where the fair definition boundary is>"
    }}
  ],
  "gov_model": {{
    "needed": <true|false>,
    "mechanism": ["<specific policy mechanism>"],
    "enforcement": ["<how to enforce>"],
    "metrics_of_success": ["<how to measure if it worked>"]
  }},
  "opp_strategies": [
    {{
      "strategy": "<strategy name>",
      "type": "<principled|practical|alternative_model>",
      "how": "<specific execution for THIS motion>",
      "impact": "<what this achieves>"
    }}
  ],
  "extensions": {{
    "OG": ["<what OG should establish>"],
    "OO": ["<what OO should establish>"],
    "CG": ["<what CG can extend with — new angle, deeper principle>"],
    "CO": ["<what CO can extend with — systemic critique, new stakeholder>"]
  }},
  "pois": [
    {{
      "poi": "<exact question to ask, specific to motion>",
      "targets": "<what it attacks: model|assumption|principle|impact|feasibility>",
      "best_timing": "<when to ask: early/mid/late + which speech>"
    }}
  ],
  "weighing": [
    "<specific weighing metric for THIS debate>"
  ],
  "difficulty": {{
    "complexity": <1-10>,
    "tech_knowledge": <1-10>,
    "abstraction": <1-10>
  }},
  "bias": {{
    "burden_gov": <1-10>,
    "burden_opp": <1-10>,
    "ground_gov": <1-10>,
    "ground_opp": <1-10>
  }},
  "quality_checks": {{
    "specificity_score": <0.0-1.0>,
    "hallucination_risk": "<low|medium|high>",
    "notes": ["<any caveats>"]
  }}
}}

RULES:
- Generate 2-3 interpretations (one standard, one alternative).
- Generate 3-6 clash axes, each specific to the motion's content.
- POIs must contain real questions referencing motion entities, NOT "[affected group]" style placeholders.
- If requires_model is false, set gov_model.needed to false and leave mechanism/enforcement/metrics empty.
- Extensions should reflect BP team roles and comparative judging norms.
- Every section must be SPECIFIC to "{motion_text}" — no generic debate advice.
- Output ONLY the JSON object."""


# =============================================================================
# Prompt D — Validator / Repair (JSON patch)
# =============================================================================

PROMPT_D_SYSTEM = """You are a debate report quality auditor. You check Motion Doctor reports
for specificity, fairness, and accuracy. Output valid JSON only."""

PROMPT_D_USER = """Validate this Motion Doctor report and fix any problems.

ORIGINAL MOTION: "{motion_text}"
{infoslide_section}

REPORT TO VALIDATE:
{report_json}

CHECK THESE RULES:
1. SPECIFICITY: Every clash area, POI, and strategy must reference specific entities/concepts from the motion text. No generic "[affected group]" or "[X]" placeholders.
2. FAIRNESS: Definition traps must not secretly favor one side. Interpretations must preserve both gov and opp ground.
3. NO HALLUCINATION: Don't invent actors or mechanisms not implied by the motion.
4. AMBIGUITY: If the motion has ambiguous terms, the report must acknowledge them in interpretations and hidden_assumptions.
5. GOV MODEL: gov_model.needed must be true ONLY if the motion is a policy/actor motion requiring a concrete mechanism.
6. COMPLETENESS: All sections must have content (not empty arrays).
7. MOTION-AWARENESS: At least 3 keywords from the motion text should appear across the report sections.

Produce a JSON response:
{{
  "is_valid": <true|false>,
  "issues_found": [
    {{
      "section": "<which section has the problem>",
      "issue": "<what's wrong>",
      "severity": "<critical|warning|minor>"
    }}
  ],
  "repaired_sections": {{
    "<section_name>": <corrected JSON for that section>
  }}
}}

If the report passes all checks, return {{"is_valid": true, "issues_found": [], "repaired_sections": {{}}}}.
If issues are found, include the corrected content in repaired_sections.
Output ONLY the JSON object."""


# =============================================================================
# Pipeline Orchestrator
# =============================================================================

class MotionDoctorPipeline:
    """Orchestrates the 4-prompt Motion Doctor pipeline."""

    def __init__(self):
        self.api_key = environ.get('OPENAI_API_KEY') or environ.get('ANTHROPIC_API_KEY')
        self.provider = 'anthropic' if environ.get('ANTHROPIC_API_KEY') else 'openai'
        self.model_version = self._get_model_name()

    def _get_model_name(self):
        if self.provider == 'anthropic':
            return environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
        return environ.get('OPENAI_MODEL', 'gpt-4o')

    def run(self, motion_text, debate_format='bp', info_slide='', archetypes=None, similar_motions=None):
        """Execute the full 4-prompt pipeline. Returns (report_dict, metadata_dict)."""
        start = time.time()
        metadata = {
            'model_version': self.model_version,
            'provider': self.provider,
            'stages': {},
        }

        infoslide_section = f'Info Slide: "{info_slide}"' if info_slide else 'Info Slide: (none provided)'

        # === Stage A: Motion Profiler ===
        try:
            profile = self._run_prompt_a(motion_text, debate_format, infoslide_section)
            metadata['stages']['profiler'] = 'success'
        except Exception as e:
            logger.warning(f"Prompt A (profiler) failed: {e}")
            profile = self._fallback_profile(motion_text, debate_format)
            metadata['stages']['profiler'] = f'fallback: {e}'

        # === Stage B: Planner ===
        archetypes_json = json.dumps(archetypes or [], indent=2)
        similar_motions_str = '\n'.join(similar_motions or ['(no similar motions available)'])

        try:
            plan = self._run_prompt_b(motion_text, debate_format, infoslide_section,
                                       profile, archetypes_json, similar_motions_str)
            metadata['stages']['planner'] = 'success'
        except Exception as e:
            logger.warning(f"Prompt B (planner) failed: {e}")
            plan = self._fallback_plan(motion_text, profile)
            metadata['stages']['planner'] = f'fallback: {e}'

        # === Stage C: Report Generator ===
        try:
            report = self._run_prompt_c(motion_text, debate_format, infoslide_section,
                                         plan, archetypes_json)
            metadata['stages']['generator'] = 'success'
        except Exception as e:
            logger.warning(f"Prompt C (generator) failed: {e}")
            report = self._fallback_report(motion_text, debate_format, profile, plan)
            metadata['stages']['generator'] = f'fallback: {e}'

        # === Stage D: Validator / Repair ===
        try:
            validation = self._run_prompt_d(motion_text, infoslide_section, report)
            metadata['stages']['validator'] = 'success'
            if not validation.get('is_valid', True):
                metadata['validation_issues'] = validation.get('issues_found', [])
                # Apply repairs
                for section, content in validation.get('repaired_sections', {}).items():
                    if section in report:
                        report[section] = content
                        logger.info(f"Repaired section: {section}")
        except Exception as e:
            logger.warning(f"Prompt D (validator) failed: {e}")
            metadata['stages']['validator'] = f'skipped: {e}'

        elapsed_ms = int((time.time() - start) * 1000)
        metadata['pipeline_duration_ms'] = elapsed_ms
        metadata['profile'] = profile
        metadata['plan'] = plan

        return report, metadata

    # -------------------------------------------------------------------------
    # AI API Call
    # -------------------------------------------------------------------------

    def _call_llm(self, system_prompt, user_prompt):
        """Call the configured LLM and return parsed JSON."""
        if not self.api_key:
            raise RuntimeError("No AI API key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)")

        if self.provider == 'anthropic':
            return self._call_anthropic(system_prompt, user_prompt)
        return self._call_openai(system_prompt, user_prompt)

    def _call_openai(self, system_prompt, user_prompt):
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_version,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def _call_anthropic(self, system_prompt, user_prompt):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model_version,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=4096,
        )
        content = response.content[0].text
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
        return json.loads(content)

    # -------------------------------------------------------------------------
    # Pipeline Stages
    # -------------------------------------------------------------------------

    def _run_prompt_a(self, motion_text, debate_format, infoslide_section):
        user_prompt = PROMPT_A_USER.format(
            motion_text=motion_text,
            infoslide_section=infoslide_section,
            format=debate_format,
        )
        return self._call_llm(PROMPT_A_SYSTEM, user_prompt)

    def _run_prompt_b(self, motion_text, debate_format, infoslide_section,
                       profile, archetypes_json, similar_motions):
        user_prompt = PROMPT_B_USER.format(
            motion_text=motion_text,
            infoslide_section=infoslide_section,
            format=debate_format,
            profile_json=json.dumps(profile, indent=2),
            archetypes_json=archetypes_json,
            similar_motions=similar_motions,
        )
        return self._call_llm(PROMPT_B_SYSTEM, user_prompt)

    def _run_prompt_c(self, motion_text, debate_format, infoslide_section,
                       plan, archetypes_json):
        user_prompt = PROMPT_C_USER.format(
            motion_text=motion_text,
            infoslide_section=infoslide_section,
            format=debate_format,
            plan_json=json.dumps(plan, indent=2),
            archetypes_json=archetypes_json,
        )
        return self._call_llm(PROMPT_C_SYSTEM, user_prompt)

    def _run_prompt_d(self, motion_text, infoslide_section, report):
        user_prompt = PROMPT_D_USER.format(
            motion_text=motion_text,
            infoslide_section=infoslide_section,
            report_json=json.dumps(report, indent=2),
        )
        return self._call_llm(PROMPT_D_SYSTEM, user_prompt)

    # -------------------------------------------------------------------------
    # Fallback Generators (when AI is unavailable)
    # -------------------------------------------------------------------------

    def _fallback_profile(self, motion_text, debate_format):
        """Template-based classifier fallback."""
        text_lower = motion_text.lower().strip()

        # Detect motion type from prefix
        if text_lower.startswith(('thw ', 'this house would')):
            motion_type = 'policy'
        elif text_lower.startswith(('thbt ', 'this house believes that')):
            motion_type = 'value'
        elif text_lower.startswith(('thr ', 'this house regrets')):
            motion_type = 'regret'
        elif text_lower.startswith(('ths ', 'this house supports')):
            motion_type = 'value'
        else:
            motion_type = 'unclear'

        # Extract basic keywords
        stop_words = {'this', 'house', 'would', 'that', 'the', 'a', 'an', 'of', 'to',
                       'in', 'for', 'on', 'with', 'at', 'by', 'its', 'it', 'is', 'are',
                       'was', 'be', 'has', 'had', 'do', 'does', 'all', 'should', 'not',
                       'believes', 'regrets', 'supports', 'prefers', 'opposes'}
        words = [w.strip('.,!?:;()[]"\'') for w in motion_text.split()
                 if len(w) > 2 and w.lower() not in stop_words]
        keywords = list(dict.fromkeys(words))[:10]

        requires_model = motion_type in ('policy', 'actor')

        return {
            'format': debate_format,
            'motion_type': motion_type,
            'domain_primary': 'unclassified',
            'domain_secondary': [],
            'actor': '',
            'action': '',
            'object': '',
            'scope': {
                'geography': 'unspecified',
                'timeframe': 'unspecified',
                'subjects': 'unspecified',
                'exceptions': ['none_specified'],
            },
            'requires_model': requires_model,
            'ambiguity_flags': ['classification done via fallback — AI unavailable'],
            'keywords': keywords,
            'confidence': 0.3,
        }

    def _fallback_plan(self, motion_text, profile):
        """Template-based planner fallback."""
        keywords = profile.get('keywords', [])
        motion_type = profile.get('motion_type', 'unclear')

        return {
            'clash_axes_to_cover': [
                {'axis': 'Principled vs. pragmatic evaluation', 'priority': 'high', 'source': 'fallback'},
                {'axis': 'Individual rights vs. collective welfare', 'priority': 'high', 'source': 'fallback'},
                {'axis': 'Short-term harm vs. long-term benefit', 'priority': 'medium', 'source': 'fallback'},
            ],
            'stakeholders_to_analyze': [
                {'group': 'Directly affected individuals', 'relevance': 'Primary impact group'},
                {'group': 'Government / implementing body', 'relevance': 'Responsible for execution'},
                {'group': 'Broader society', 'relevance': 'Systemic effects'},
            ],
            'model_needed': profile.get('requires_model', False),
            'model_guidance': 'Concrete policy mechanism required' if profile.get('requires_model') else None,
            'interpretations_to_offer': [
                {'reading': 'Broad standard reading of the motion terms', 'is_standard': True},
                {'reading': 'Narrower reading focusing on most contested aspect', 'is_standard': False},
            ],
            'things_to_avoid': [
                'Generic arguments not tied to the specific motion',
                'Ignoring the strongest opposing argument',
            ],
            'definition_risks': [
                f'Over-narrowing definitions to avoid clash on {keywords[0] if keywords else "key terms"}',
            ],
            'weighing_approach': 'Compare magnitude, probability, and reversibility of harms/benefits',
            'extension_strategy': 'Develop new stakeholder analysis or deeper principled framework',
            'ambiguity_notes': 'Motion classification done via fallback; human review recommended' if motion_type == 'unclear' else None,
        }

    def _fallback_report(self, motion_text, debate_format, profile, plan):
        """Generate a structured report from profile + plan without AI."""
        keywords = profile.get('keywords', [])
        kw_str = ', '.join(keywords[:5]) if keywords else 'the motion terms'
        motion_type = profile.get('motion_type', 'unclear')
        requires_model = profile.get('requires_model', False)

        clashes = []
        for clash in plan.get('clash_axes_to_cover', []):
            clashes.append({
                'axis': clash['axis'],
                'gov_claim': f"Government argues that action on {kw_str} produces net positive outcomes",
                'opp_claim': f"Opposition argues that the costs of intervening on {kw_str} outweigh benefits",
            })
        if not clashes:
            clashes = [{'axis': 'Core value trade-off', 'gov_claim': 'Change is net positive', 'opp_claim': 'Status quo is preferable'}]

        return {
            'interpretations': [
                {
                    'title': 'Standard reading',
                    'definition': f'Standard interpretation of "{motion_text[:80]}"',
                    'fairness_notes': 'This reading preserves ground for both sides',
                },
                {
                    'title': 'Alternative reading',
                    'definition': f'Narrower interpretation focusing on the most contested element of {kw_str}',
                    'fairness_notes': 'May limit opposition ground — teams should flag this',
                },
            ],
            'clash_areas': clashes,
            'hidden_assumptions': [
                f'The motion assumes a specific understanding of {keywords[0] if keywords else "key terms"}',
                'There is an implicit status quo being challenged',
                'The scope and mechanism may be interpreted differently by teams',
            ],
            'definition_traps': [
                {
                    'trap': f'Defining {keywords[0] if keywords else "the key term"} too narrowly to avoid opposition ground',
                    'why_bad': 'Removes meaningful clash from the debate',
                    'fair_line': 'Use the broadest reasonable interpretation that still allows for focused analysis',
                },
            ],
            'gov_model': {
                'needed': requires_model,
                'mechanism': [f'Concrete mechanism for implementing change regarding {kw_str}'] if requires_model else [],
                'enforcement': ['Designated enforcement body with monitoring'] if requires_model else [],
                'metrics_of_success': ['Measurable reduction in identified harms'] if requires_model else [],
            },
            'opp_strategies': [
                {
                    'strategy': 'Status quo defense',
                    'type': 'practical',
                    'how': f'Show existing frameworks already address concerns about {kw_str}',
                    'impact': 'Undermines necessity of gov proposal',
                },
                {
                    'strategy': 'Principled objection',
                    'type': 'principled',
                    'how': f'Argue the motion violates core principles (autonomy, liberty, etc.)',
                    'impact': 'Creates values-level burden gov must overcome',
                },
                {
                    'strategy': 'Counter-model',
                    'type': 'alternative_model',
                    'how': 'Propose less restrictive alternative that achieves similar goals',
                    'impact': 'Shows gov solution is disproportionate',
                },
            ],
            'extensions': {
                'OG': [f'Establish the core case: mechanism + primary harms of status quo regarding {kw_str}'],
                'OO': [f'Attack feasibility and show unintended consequences of gov model on {kw_str}'],
                'CG': ['Introduce deeper principled analysis or new stakeholder group not covered by OG'],
                'CO': ['Systemic critique or long-term consequences that OO missed'],
            },
            'pois': [
                {'poi': f'What specific mechanism do you propose for addressing {keywords[0] if keywords else "this issue"}?', 'targets': 'model', 'best_timing': 'early — during government constructive'},
                {'poi': f'How do you account for unintended consequences on {keywords[1] if len(keywords) > 1 else "affected groups"}?', 'targets': 'impact', 'best_timing': 'mid — during extension speeches'},
                {'poi': f'Where is your principled line for when this applies versus when it doesn\'t?', 'targets': 'principle', 'best_timing': 'mid — during CG/CO'},
                {'poi': 'What empirical evidence supports your causal chain?', 'targets': 'assumption', 'best_timing': 'early — during PM/LO'},
                {'poi': 'Are you assuming perfect implementation?', 'targets': 'feasibility', 'best_timing': 'mid — during MG'},
            ],
            'weighing': [
                f'Scope: how many people are affected by changes to {kw_str}',
                'Severity: depth of harm or benefit for those affected',
                'Probability: likelihood of predicted outcomes actually occurring',
                'Reversibility: whether negative consequences can be corrected',
            ],
            'difficulty': {
                'complexity': 5,
                'tech_knowledge': 4,
                'abstraction': 5,
            },
            'bias': {
                'burden_gov': 6,
                'burden_opp': 5,
                'ground_gov': 6,
                'ground_opp': 5,
            },
            'quality_checks': {
                'specificity_score': 0.35,
                'hallucination_risk': 'low',
                'notes': [
                    'Generated via template fallback — AI service unavailable',
                    'Sections contain motion keywords but lack deep analysis',
                    'Human review recommended for coaching use',
                ],
            },
        }
