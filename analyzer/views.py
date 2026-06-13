import logging

from defusedxml.ElementTree import fromstring
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


ANALYSIS_FEATURES = [
    'Team rankings', 'Speaker scores',
    'Adjudicator panels', 'Round-by-round',
    'Motion log', 'Format stats',
]


class AnalyzeView(TemplateView):
    template_name = 'analyzer/analyze.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['analysis_features'] = ANALYSIS_FEATURES
        return ctx


class AnalyzeResultsView(View):
    def get(self, request):
        return redirect('analyze-home')

    def post(self, request):
        xml_file = request.FILES.get('xml_file')
        if not xml_file:
            return HttpResponseBadRequest('No file uploaded.')

        if xml_file.size > 10 * 1024 * 1024:  # 10 MB guard
            return HttpResponseBadRequest('File too large (max 10 MB).')

        try:
            content = xml_file.read()
            root = fromstring(content)
        except Exception as e:
            logger.warning('AnalyzeResultsView: XML parse error — %s', e)
            return render(request, 'analyzer/analyze.html', {
                'error': f'Could not parse XML: {e}',
                'analysis_features': ANALYSIS_FEATURES,
            })

        try:
            data = _parse_tournament_xml(root)
        except Exception as e:
            logger.exception('AnalyzeResultsView: analysis error')
            return render(request, 'analyzer/analyze.html', {
                'error': f'Analysis error: {e}',
                'analysis_features': ANALYSIS_FEATURES,
            })

        return render(request, 'analyzer/results.html', {'data': data})


# ──────────────────────────────────────────────────────────────────────────────
# XML parser — supports Tabbycat XML export AND DebateXML (spec.xsd) format
# ──────────────────────────────────────────────────────────────────────────────

def _parse_tournament_xml(root):
    """Return a rich analysis dict from a Tabbycat or DebateXML export."""

    data = {
        'name': root.get('name', 'Unknown Tournament'),
        'short': root.get('short', root.get('name', '')),
        'style': root.get('style', '').upper() or 'Unknown',
        'institutions': {},
        'teams': {},
        'speakers': {},
        'adjudicators': {},
        'motions': {},
        'rounds': [],
    }

    # ── institutions ─────────────────────────────────────────────────────────
    for inst in root.findall('.//institution'):
        iid = inst.get('id', '')
        if iid:
            data['institutions'][iid] = {
                'name': (inst.text or '').strip(),
                'reference': inst.get('reference', ''),
                'region': inst.get('region', ''),
            }

    # ── participants (Tabbycat format: flat children of root) ────────────────
    for team_el in root.findall('.//team'):
        tid = team_el.get('id', '')
        if not tid:
            continue
        name = team_el.get('name', (team_el.text or '').strip())
        data['teams'][tid] = {
            'id': tid,
            'name': name,
            'code': team_el.get('code', ''),
            'institution_id': (team_el.get('institutions', '') or '').split()[0],
            'wins': 0, 'losses': 0, 'draws': 0,
            'rounds_competed': 0,
            'speaker_ids': [],
        }
        for sp_el in team_el.findall('speaker'):
            sid = sp_el.get('id', '')
            if not sid:
                continue
            data['speakers'][sid] = {
                'id': sid,
                'name': (sp_el.text or '').strip(),
                'gender': sp_el.get('gender', ''),
                'team_id': tid,
                'total_score': 0.0,
                'rounds_debated': 0,
                'scores': [],
            }
            data['teams'][tid]['speaker_ids'].append(sid)

    # ── adjudicators ─────────────────────────────────────────────────────────
    for adj_el in root.findall('.//adjudicator'):
        aid = adj_el.get('id', '')
        if not aid:
            continue
        data['adjudicators'][aid] = {
            'id': aid,
            'name': adj_el.get('name', (adj_el.text or '').strip()),
            'independent': adj_el.get('independent', 'false') == 'true',
            'base_score': _safe_float(adj_el.get('score', '0')),
            'rounds_judged': 0,
            'rounds_chaired': 0,
        }

    # ── motions ──────────────────────────────────────────────────────────────
    for mot_el in root.findall('.//motion'):
        mid = mot_el.get('id', '')
        if mid:
            data['motions'][mid] = {
                'reference': mot_el.get('reference', ''),
                'text': (mot_el.text or '').strip(),
            }

    # ── rounds + debates ─────────────────────────────────────────────────────
    for round_el in root.findall('round'):
        round_info = {
            'name': round_el.get('name', ''),
            'abbreviation': round_el.get('abbreviation', ''),
            'elimination': round_el.get('elimination', 'false') == 'true',
            'start': round_el.get('start', ''),
            'debates': [],
            'debate_count': 0,
        }

        for debate_el in round_el.findall('debate'):
            did = debate_el.get('id', '')
            venue_id = debate_el.get('venue', '')
            motion_id = debate_el.get('motion', '')
            motion_text = data['motions'].get(motion_id, {}).get('text', '') or \
                          data['motions'].get(motion_id, {}).get('reference', '')

            adj_ids = debate_el.get('adjudicators', '').split()
            for i, aid in enumerate(adj_ids):
                if aid in data['adjudicators']:
                    data['adjudicators'][aid]['rounds_judged'] += 1
                    if i == 0:
                        data['adjudicators'][aid]['rounds_chaired'] += 1

            debate_info = {
                'id': did,
                'motion': motion_text,
                'sides': [],
            }

            for side_el in debate_el.findall('side'):
                tid = side_el.get('team', '')
                result = side_el.get('result', '')
                side_name = side_el.get('side', '')

                if tid in data['teams']:
                    data['teams'][tid]['rounds_competed'] += 1
                    if result == 'win':
                        data['teams'][tid]['wins'] += 1
                    elif result in ('loss', 'lose'):
                        data['teams'][tid]['losses'] += 1
                    elif result == 'draw':
                        data['teams'][tid]['draws'] += 1

                side_scores = []
                for ballot_el in side_el.findall('ballot'):
                    if ballot_el.get('ignored', 'false') == 'true':
                        continue
                    for score_el in ballot_el.findall('score'):
                        sid = score_el.get('speaker', '')
                        val = _safe_float(score_el.text)
                        if sid and sid in data['speakers']:
                            data['speakers'][sid]['total_score'] += val
                            data['speakers'][sid]['rounds_debated'] += 1
                            data['speakers'][sid]['scores'].append(val)
                        side_scores.append({'speaker': sid, 'score': val})

                debate_info['sides'].append({
                    'team_id': tid,
                    'team_name': data['teams'].get(tid, {}).get('name', tid),
                    'result': result,
                    'side': side_name,
                    'scores': side_scores,
                })

            round_info['debates'].append(debate_info)
            round_info['debate_count'] += 1

        data['rounds'].append(round_info)

    # ── rankings ─────────────────────────────────────────────────────────────
    team_list = []
    for tid, t in data['teams'].items():
        inst_name = data['institutions'].get(t['institution_id'], {}).get('name', '')
        team_list.append({
            'name': t['name'],
            'code': t['code'],
            'institution': inst_name,
            'wins': t['wins'],
            'losses': t['losses'],
            'draws': t['draws'],
            'rounds': t['rounds_competed'],
        })
    team_list.sort(key=lambda x: (-x['wins'], -(x['wins'] / max(x['rounds'], 1))))
    data['team_rankings'] = team_list

    speaker_list = []
    for sid, s in data['speakers'].items():
        if s['rounds_debated'] == 0:
            continue
        avg = s['total_score'] / s['rounds_debated']
        team_name = data['teams'].get(s['team_id'], {}).get('name', '')
        speaker_list.append({
            'name': s['name'],
            'team': team_name,
            'total': round(s['total_score'], 1),
            'average': round(avg, 2),
            'rounds': s['rounds_debated'],
            'gender': s['gender'],
        })
    speaker_list.sort(key=lambda x: -x['total'])
    data['speaker_rankings'] = speaker_list

    adj_list = []
    for aid, a in data['adjudicators'].items():
        if a['rounds_judged'] == 0:
            continue
        adj_list.append({
            'name': a['name'],
            'base_score': a['base_score'],
            'rounds_judged': a['rounds_judged'],
            'rounds_chaired': a['rounds_chaired'],
            'independent': a['independent'],
        })
    adj_list.sort(key=lambda x: -x['rounds_judged'])
    data['adj_rankings'] = adj_list

    prelim_rounds = [r for r in data['rounds'] if not r['elimination']]
    elim_rounds = [r for r in data['rounds'] if r['elimination']]

    data['stats'] = {
        'total_teams': len(data['teams']),
        'total_speakers': len(data['speakers']),
        'total_adjudicators': len(data['adjudicators']),
        'total_rounds': len(data['rounds']),
        'prelim_rounds': len(prelim_rounds),
        'elim_rounds': len(elim_rounds),
        'total_debates': sum(r['debate_count'] for r in data['rounds']),
        'total_institutions': len(data['institutions']),
        'total_motions': len(data['motions']),
    }

    return data


def _safe_float(val, default=0.0):
    try:
        return float(val or default)
    except (TypeError, ValueError):
        return default
