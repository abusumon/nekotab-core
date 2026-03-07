import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import OrganizationRegistrationForm

from .models import (
    Organization, OrganizationMembership,
    get_user_organizations, user_is_org_admin, user_is_org_owner,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class OrgAccessMixin:
    """Mixin that resolves the org from URL and checks membership."""

    def get_organization(self):
        slug = self.kwargs['org_slug']
        return get_object_or_404(Organization, slug=slug)

    def dispatch(self, request, *args, **kwargs):
        # Anonymous users are handled by LoginRequiredMixin on the view,
        # but guard defensively in case this mixin is used standalone.
        if not request.user.is_authenticated:
            raise Http404
        self.organization = self.get_organization()
        if not OrganizationMembership.objects.filter(
            organization=self.organization, user=request.user,
        ).exists():
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class OrgAdminMixin(OrgAccessMixin):
    """Requires ADMIN or OWNER role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise Http404
        self.organization = self.get_organization()
        if not user_is_org_admin(request.user, self.organization):
            return HttpResponseForbidden("You don't have admin access to this organization.")
        return super(OrgAccessMixin, self).dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class OrganizationListView(LoginRequiredMixin, ListView):
    """List organizations the current user belongs to."""
    template_name = 'organizations/list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        return get_user_organizations(self.request.user).prefetch_related(
            'memberships', 'tournaments',
        )


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    """Create a new organization. The creator becomes OWNER."""
    model = Organization
    fields = ['name', 'slug']
    template_name = 'organizations/create.html'

    def form_valid(self, form):
        org = form.save()
        OrganizationMembership.objects.create(
            organization=org,
            user=self.request.user,
            role=OrganizationMembership.Role.OWNER,
        )
        messages.success(self.request, _("Organization created successfully."))
        return redirect('org-detail', org_slug=org.slug)


class OrganizationDetailView(LoginRequiredMixin, OrgAccessMixin, DetailView):
    """View org details + tournament list."""
    model = Organization
    template_name = 'organizations/detail.html'
    context_object_name = 'organization'
    slug_url_kwarg = 'org_slug'

    def get_object(self, queryset=None):
        return self.organization

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tournaments'] = self.organization.tournaments.filter(active=True)
        ctx['inactive_tournaments'] = self.organization.tournaments.filter(active=False)
        ctx['members'] = self.organization.memberships.select_related('user').order_by('role')
        ctx['is_admin'] = user_is_org_admin(self.request.user, self.organization)
        ctx['is_owner'] = user_is_org_owner(self.request.user, self.organization)
        ctx['my_membership'] = OrganizationMembership.objects.filter(
            organization=self.organization, user=self.request.user,
        ).first()
        return ctx


class OrganizationUpdateView(LoginRequiredMixin, OrgAdminMixin, UpdateView):
    """Edit org name/slug — admin/owner only."""
    model = Organization
    fields = ['name', 'slug']
    template_name = 'organizations/edit.html'
    slug_url_kwarg = 'org_slug'

    def get_object(self, queryset=None):
        return self.organization

    def get_success_url(self):
        return reverse('org-detail', kwargs={'org_slug': self.object.slug})


class OrganizationMembersView(LoginRequiredMixin, OrgAccessMixin, DetailView):
    """View member list."""
    model = Organization
    template_name = 'organizations/members.html'
    slug_url_kwarg = 'org_slug'

    def get_object(self, queryset=None):
        return self.organization

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['organization'] = self.organization
        ctx['members'] = self.organization.memberships.select_related('user').order_by('role')
        ctx['is_admin'] = user_is_org_admin(self.request.user, self.organization)
        ctx['roles'] = OrganizationMembership.Role.choices
        return ctx


class OrganizationAddMemberView(LoginRequiredMixin, OrgAdminMixin, View):
    """Add a member to the org (POST only)."""

    def post(self, request, *args, **kwargs):
        username_or_email = request.POST.get('username', '').strip()
        role = request.POST.get('role', OrganizationMembership.Role.MEMBER)

        # Validate role
        valid_roles = [r[0] for r in OrganizationMembership.Role.choices]
        if role not in valid_roles:
            role = OrganizationMembership.Role.MEMBER

        # Prevent non-owners from adding owners
        if role == OrganizationMembership.Role.OWNER and not user_is_org_owner(request.user, self.organization):
            messages.error(request, _("Only the org owner can add other owners."))
            return redirect('org-members', org_slug=self.organization.slug)

        # Find user
        user = User.objects.filter(username=username_or_email).first()
        if user is None:
            user = User.objects.filter(email=username_or_email).first()
        if user is None:
            messages.error(request, _("User not found: %(query)s") % {'query': username_or_email})
            return redirect('org-members', org_slug=self.organization.slug)

        # Create membership
        _, created = OrganizationMembership.objects.get_or_create(
            organization=self.organization,
            user=user,
            defaults={'role': role},
        )
        if created:
            messages.success(request, _("%(user)s added as %(role)s.") % {
                'user': user.username, 'role': role,
            })
        else:
            messages.info(request, _("%(user)s is already a member.") % {'user': user.username})

        return redirect('org-members', org_slug=self.organization.slug)


class OrganizationRemoveMemberView(LoginRequiredMixin, OrgAdminMixin, View):
    """Remove a member from the org (POST only)."""

    def post(self, request, *args, **kwargs):
        membership = get_object_or_404(
            OrganizationMembership,
            pk=kwargs['membership_id'],
            organization=self.organization,
        )

        # Can't remove the last owner
        if membership.role == OrganizationMembership.Role.OWNER:
            owner_count = OrganizationMembership.objects.filter(
                organization=self.organization,
                role=OrganizationMembership.Role.OWNER,
            ).count()
            if owner_count <= 1:
                messages.error(request, _("Cannot remove the last owner."))
                return redirect('org-members', org_slug=self.organization.slug)

        # Only owners can remove admins
        if membership.role == OrganizationMembership.Role.ADMIN and not user_is_org_owner(request.user, self.organization):
            messages.error(request, _("Only owners can remove admins."))
            return redirect('org-members', org_slug=self.organization.slug)

        username = membership.user.username
        membership.delete()
        messages.success(request, _("%(user)s removed from organization.") % {'user': username})
        return redirect('org-members', org_slug=self.organization.slug)


class OrganizationChangeMemberRoleView(LoginRequiredMixin, OrgAdminMixin, View):
    """Change a member's role (POST only)."""

    def post(self, request, *args, **kwargs):
        membership = get_object_or_404(
            OrganizationMembership,
            pk=kwargs['membership_id'],
            organization=self.organization,
        )
        new_role = request.POST.get('role', '')
        valid_roles = [r[0] for r in OrganizationMembership.Role.choices]
        if new_role not in valid_roles:
            messages.error(request, _("Invalid role."))
            return redirect('org-members', org_slug=self.organization.slug)

        # Only owners can promote to owner or demote from owner
        if (new_role == OrganizationMembership.Role.OWNER or
                membership.role == OrganizationMembership.Role.OWNER):
            if not user_is_org_owner(request.user, self.organization):
                messages.error(request, _("Only owners can change owner roles."))
                return redirect('org-members', org_slug=self.organization.slug)

        # Prevent demoting the last owner
        if membership.role == OrganizationMembership.Role.OWNER and new_role != OrganizationMembership.Role.OWNER:
            owner_count = OrganizationMembership.objects.filter(
                organization=self.organization,
                role=OrganizationMembership.Role.OWNER,
            ).count()
            if owner_count <= 1:
                messages.error(request, _("Cannot demote the last owner."))
                return redirect('org-members', org_slug=self.organization.slug)

        membership.role = new_role
        membership.save()
        messages.success(request, _("%(user)s is now %(role)s.") % {
            'user': membership.user.username, 'role': new_role,
        })
        return redirect('org-members', org_slug=self.organization.slug)


class RegisterOrganizationView(LoginRequiredMixin, CreateView):
    """Public registration flow: create an organization workspace."""
    form_class = OrganizationRegistrationForm
    template_name = 'registration/register_organization.html'

    def form_valid(self, form):
        with transaction.atomic():
            org = form.save(commit=False)
            org.is_workspace_enabled = True
            org.save()
            OrganizationMembership.objects.create(
                organization=org,
                user=self.request.user,
                role=OrganizationMembership.Role.OWNER,
            )

        base = getattr(settings, 'SUBDOMAIN_BASE_DOMAIN', 'nekotab.app')
        return redirect(f"https://{org.slug}.{base}/tournaments/new/")
