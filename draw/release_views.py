"""One release panel on the draw page: draw, motions and self check-in.

Tabbycat already had "release draw to public" and "release motions", but only
on the Display page, and self check-in was a switch buried in Configuration.
Directors spend the round on the draw page, so the panel puts all three there
(see ``_release_panel.html``), and adds one new option:

**Release to participants only** (NekoTab Pro): the round becomes released, so
private URLs, online ballots and feedback all work, but the public draw pages
keep showing "not released" (``Round.draw_teams_only``). Every speaker and
adjudicator with an email gets their room by email, the draw is posted to the
tournament's Discord channels, and the panel offers a WhatsApp share of the
draw text (websites cannot post into WhatsApp groups themselves).
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.dispatch import Signal
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from actionlog.models import ActionLogEntry
from motions.views import ReleaseMotionsView, UnreleaseMotionsView
from notifications.models import BulkNotification
from participants.models import Adjudicator, Speaker
from tournaments.models import Round
from users.permissions import Permission
from utils.misc import build_tournament_absolute_uri, reverse_tournament
from utils.plans import new_features_visible, tournament_allows, upgrade_url

from .views import DrawStatusEdit

logger = logging.getLogger(__name__)

#: Sent after a private release. NekoTab's portal app posts the text to the
#: tournament's Discord channels and returns {'channels': n, 'ok': n}.
draw_released_to_teams = Signal()

SHARE_SESSION_KEY = 'draw_share_text_%s'


def draw_share_text(round, limit=3500):
    """Plain-text draw for WhatsApp/Discord: one line per room."""
    lines = [f"{round.tournament.short_name or round.tournament.name}: {round.name} draw"]
    if round.starts_at:
        lines.append(_("Debates start at %(time)s") % {'time': round.starts_at.strftime('%H:%M')})
    lines.append('')
    debates = round.debate_set_with_prefetches(ordering=('room_rank',), institutions=False, venues=True)
    for d in debates:
        teams = ' vs '.join(f"{dt.team.short_name} ({dt.get_side_name(round.tournament, 'abbr')})" for dt in d.debateteam_set.all())
        adjs = ', '.join(a.name for a in d.adjudicators.voting()) if hasattr(d, 'adjudicators') else ''
        room = d.venue.display_name if d.venue else _("Room TBA")
        lines.append(f"{room}: {teams}" + (f" | {_('Adj')}: {adjs}" if adjs else ''))
    text = '\n'.join(lines)
    if len(text) > limit:
        text = text[:limit - 40].rsplit('\n', 1)[0] + '\n' + _("(Full draw in your private link.)")
    return text


class _PanelMixin:
    def dispatch(self, request, *args, **kwargs):
        if not new_features_visible(request):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class DrawReleaseToTeamsView(_PanelMixin, DrawStatusEdit):
    edit_permission = Permission.RELEASE_DRAW
    action_log_type = ActionLogEntry.ActionType.DRAW_RELEASE
    round_redirect_pattern_name = 'draw'

    def post(self, request, *args, **kwargs):
        t = self.tournament
        if not tournament_allows(t, 'release_to_teams'):
            messages.info(request, _("Releasing the draw to participants only is part of NekoTab Pro."))
            return redirect(upgrade_url(t) + '?need=release')
        if self.round.draw_status not in (Round.Status.CONFIRMED, Round.Status.RELEASED):
            messages.error(request, _("Confirm the draw before releasing it."))
            return super().post(request, *args, **kwargs)

        self.round.draw_status = Round.Status.RELEASED
        self.round.draw_teams_only = True
        self.round.save(update_fields=['draw_status', 'draw_teams_only'])
        self.log_action()

        notes = [_("Released the draw to participants only. The public draw page still says it isn't out.")]
        sent = self._email_everyone() if tournament_allows(t, 'email') else 0
        if sent:
            notes.append(_("%(n)d emails are being sent with each person's room.") % {'n': sent})

        text = draw_share_text(self.round)
        request.session[SHARE_SESSION_KEY % self.round.pk] = text
        posted = 0
        for _receiver, result in draw_released_to_teams.send_robust(
                sender=self.__class__, round=self.round, text=text, user=request.user):
            if isinstance(result, dict):
                posted += result.get('ok', 0)
            elif isinstance(result, Exception):
                logger.warning("Discord post after private release failed: %s", result)
        if posted:
            notes.append(_("Posted to %(n)d Discord channel(s).") % {'n': posted})
        notes.append(_("Use “Share on WhatsApp” on the release panel to send it to your group."))
        messages.success(request, ' '.join(notes))
        return super().post(request, *args, **kwargs)

    def _email_everyone(self):
        r, t = self.round, self.tournament
        adj_ids = list(Adjudicator.objects.filter(debateadjudicator__debate__round=r).exclude(email__isnull=True)
                       .exclude(email='').values_list('pk', flat=True).distinct())
        spk_ids = list(Speaker.objects.filter(team__debateteam__debate__round=r).exclude(email__isnull=True)
                       .exclude(email='').values_list('pk', flat=True).distinct())
        layer = get_channel_layer()
        if adj_ids:
            path = reverse_tournament('privateurls-person-index', t, kwargs={'url_key': '0'})
            url = build_tournament_absolute_uri(self.request, t, path)[:-2]
            async_to_sync(layer.send)("notifications", {
                "type": "email", "message": BulkNotification.EventType.ADJ_DRAW,
                "extra": {'round_id': r.id, 'url': url}, "send_to": adj_ids,
                "subject": t.pref('adj_email_subject'), "body": t.pref('adj_email_message'),
            })
        if spk_ids:
            async_to_sync(layer.send)("notifications", {
                "type": "email", "message": BulkNotification.EventType.TEAM_DRAW,
                "extra": {'round_id': r.id}, "send_to": spk_ids,
                "subject": t.pref('team_draw_email_subject'), "body": t.pref('team_draw_email_message'),
            })
        return len(adj_ids) + len(spk_ids)


class DrawMakePublicView(_PanelMixin, DrawStatusEdit):
    edit_permission = Permission.RELEASE_DRAW
    action_log_type = ActionLogEntry.ActionType.DRAW_RELEASE
    round_redirect_pattern_name = 'draw'

    def post(self, request, *args, **kwargs):
        if self.round.draw_status not in (Round.Status.CONFIRMED, Round.Status.RELEASED):
            messages.error(request, _("Confirm the draw before releasing it."))
            return super().post(request, *args, **kwargs)
        self.round.draw_status = Round.Status.RELEASED
        self.round.draw_teams_only = False
        self.round.save(update_fields=['draw_status', 'draw_teams_only'])
        self.log_action()
        messages.success(request, _("The draw is now public."))
        return super().post(request, *args, **kwargs)


class DrawPanelUnreleaseView(_PanelMixin, DrawStatusEdit):
    edit_permission = Permission.UNRELEASE_DRAW
    action_log_type = ActionLogEntry.ActionType.DRAW_UNRELEASE
    round_redirect_pattern_name = 'draw'

    def post(self, request, *args, **kwargs):
        if self.round.draw_status == Round.Status.RELEASED:
            self.round.draw_status = Round.Status.CONFIRMED
            self.round.draw_teams_only = False
            self.round.save(update_fields=['draw_status', 'draw_teams_only'])
            self.log_action()
            messages.success(request, _("Unreleased the draw."))
        return super().post(request, *args, **kwargs)


class PanelReleaseMotionsView(_PanelMixin, ReleaseMotionsView):
    round_redirect_pattern_name = 'draw'


class PanelUnreleaseMotionsView(_PanelMixin, UnreleaseMotionsView):
    edit_permission = Permission.UNRELEASE_MOTION
    round_redirect_pattern_name = 'draw'


class SelfCheckinToggleView(_PanelMixin, DrawStatusEdit):
    """Open or close participant self check-in (the ``public_checkins_submit`` preference)."""
    view_permission = Permission.VIEW_CHECKIN
    edit_permission = Permission.EDIT_PARTICIPANT_CHECKIN
    action_log_type = ActionLogEntry.ActionType.OPTIONS_EDIT

    def post(self, request, *args, **kwargs):
        turn_on = request.POST.get('state') == 'on'
        self.tournament.preferences['data_entry__public_checkins_submit'] = turn_on
        self.log_action()
        if turn_on:
            messages.success(request, _("Self check-in is open: participants can check in from their private URLs."))
        else:
            messages.success(request, _("Self check-in is closed."))
        nxt = request.POST.get('next', '')
        if nxt.startswith('/') and not nxt.startswith('//'):
            return redirect(nxt)
        return super().post(request, *args, **kwargs)


def release_panel_context(request, round):
    """Context for ``_release_panel.html``, or None when the panel is hidden."""
    if not new_features_visible(request):
        return None
    from urllib.parse import quote
    t = round.tournament
    share = request.session.get(SHARE_SESSION_KEY % round.pk) if round.draw_teams_only else None
    return {
        'teams_allowed': tournament_allows(t, 'release_to_teams'),
        'upgrade_url': upgrade_url(t),
        'share_text': share,
        'whatsapp_url': ('https://wa.me/?text=' + quote(share)) if share else '',
        'self_checkin': t.pref('public_checkins_submit'),
        'motion_count': round.motion_set.count(),
    }
