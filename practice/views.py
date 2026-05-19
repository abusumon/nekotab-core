from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from organizations.models import OrganizationMembership
from organizations.workspace_mixins import WorkspaceAccessMixin, WorkspaceAdminMixin

from .forms import PracticeSessionForm, ScoreEntryForm, SessionRoomForm
from .models import PracticeSession, SessionParticipant, SessionRoom, SpeakerScore


class PracticeSessionListView(WorkspaceAccessMixin, ListView):
    template_name = 'organizations/workspace/practice/list.html'
    context_object_name = 'sessions'

    def get_queryset(self):
        return PracticeSession.objects.filter(
            organization=self.organization,
        ).prefetch_related('rooms', 'participants')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'practice'
        qs = self.get_queryset()
        ctx['total_count'] = qs.count()
        ctx['completed_count'] = qs.filter(status='completed').count()
        ctx['scheduled_count'] = qs.filter(status='scheduled').count()
        return ctx


class PracticeSessionCreateView(WorkspaceAdminMixin, CreateView):
    template_name = 'organizations/workspace/practice/create.html'
    form_class = PracticeSessionForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'practice'
        return ctx

    def form_valid(self, form):
        session = form.save(commit=False)
        session.organization = self.organization
        session.created_by = self.request.user
        session.save()
        messages.success(self.request, _("Practice session created."))
        return redirect(f'/practice/{session.pk}/')


class PracticeSessionDetailView(WorkspaceAccessMixin, DetailView):
    template_name = 'organizations/workspace/practice/detail.html'
    context_object_name = 'session'

    def get_object(self):
        return get_object_or_404(
            PracticeSession,
            pk=self.kwargs['pk'],
            organization=self.organization,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_tab'] = 'practice'
        session = self.object
        ctx['rooms'] = session.rooms.prefetch_related('participants__score', 'participants__membership__user')
        ctx['all_members'] = self.organization.memberships.select_related('user').order_by('user__first_name')
        ctx['participant_ids'] = set(session.participants.values_list('membership_id', flat=True))
        return ctx


class AddRoomView(WorkspaceAdminMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(PracticeSession, pk=pk, organization=self.organization)
        seq = session.rooms.count() + 1
        room = SessionRoom.objects.create(
            session=session,
            name=f"Room {seq}",
            seq=seq,
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'id': room.pk, 'name': room.name, 'seq': room.seq})
        return redirect(f'/practice/{pk}/')


class AddParticipantView(WorkspaceAdminMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(PracticeSession, pk=pk, organization=self.organization)
        membership_id = request.POST.get('membership_id')
        role = request.POST.get('role', 'debater')
        room_id = request.POST.get('room_id') or None
        membership = get_object_or_404(OrganizationMembership, pk=membership_id, organization=self.organization)
        room = SessionRoom.objects.filter(pk=room_id, session=session).first() if room_id else None
        SessionParticipant.objects.get_or_create(
            session=session,
            membership=membership,
            defaults={'role': role, 'room': room},
        )
        return redirect(f'/practice/{pk}/')


class ScoreInputView(WorkspaceAdminMixin, View):
    template_name = 'organizations/workspace/practice/score.html'

    def get(self, request, pk):
        from django.shortcuts import render
        session = get_object_or_404(PracticeSession, pk=pk, organization=self.organization)
        debaters = session.participants.filter(role='debater').select_related(
            'membership__user', 'room',
        ).prefetch_related('score')
        score_forms = []
        for p in debaters:
            instance = getattr(p, 'score', None)
            form = ScoreEntryForm(instance=instance, prefix=f'p_{p.pk}')
            score_forms.append((p, form))
        ctx = {
            'session': session,
            'score_forms': score_forms,
            'active_tab': 'practice',
            'organization': self.organization,
            'membership': self.membership,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        session = get_object_or_404(PracticeSession, pk=pk, organization=self.organization)
        debaters = session.participants.filter(role='debater').select_related('membership__user')
        errors = False
        with transaction.atomic():
            for p in debaters:
                instance = getattr(p, 'score', None)
                form = ScoreEntryForm(request.POST, instance=instance, prefix=f'p_{p.pk}')
                if form.is_valid():
                    score_obj = form.save(commit=False)
                    score_obj.participant = p
                    score_obj.submitted_by = request.user
                    score_obj.save()
                else:
                    errors = True
        if errors:
            messages.warning(request, _("Some scores could not be saved. Please check the form."))
        else:
            messages.success(request, _("Scores saved."))
        return redirect(f'/practice/{pk}/')
