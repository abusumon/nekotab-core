from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseForbidden

from .models import OrganizationMembership


class WorkspaceAccessMixin:
    """Requires authenticated user + membership in the tenant organization."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        org = getattr(request, 'tenant_organization', None)
        if not org:
            raise Http404
        self.organization = org
        self.membership = OrganizationMembership.objects.filter(
            organization=org, user=request.user,
        ).first()
        if not self.membership and not request.user.is_superuser:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['organization'] = self.organization
        ctx['membership'] = self.membership
        return ctx


class WorkspaceAdminMixin(WorkspaceAccessMixin):
    """Requires ADMIN or OWNER role in the organization."""

    def dispatch(self, request, *args, **kwargs):
        # Authenticate and resolve membership first (without dispatching to the view)
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        org = getattr(request, 'tenant_organization', None)
        if not org:
            raise Http404
        self.organization = org
        self.membership = OrganizationMembership.objects.filter(
            organization=org, user=request.user,
        ).first()
        if not self.membership and not request.user.is_superuser:
            raise Http404
        # Check admin role before processing the request
        if self.membership and not self.membership.has_role_at_least(OrganizationMembership.Role.ADMIN):
            return HttpResponseForbidden("Admin access required.")
        return super(WorkspaceAccessMixin, self).dispatch(request, *args, **kwargs)


class WorkspaceOwnerMixin(WorkspaceAccessMixin):
    """Requires OWNER role."""

    def dispatch(self, request, *args, **kwargs):
        # Authenticate and resolve membership first (without dispatching to the view)
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        org = getattr(request, 'tenant_organization', None)
        if not org:
            raise Http404
        self.organization = org
        self.membership = OrganizationMembership.objects.filter(
            organization=org, user=request.user,
        ).first()
        if not self.membership and not request.user.is_superuser:
            raise Http404
        # Check owner role before processing the request
        if self.membership and self.membership.role != OrganizationMembership.Role.OWNER:
            return HttpResponseForbidden("Owner access required.")
        return super(WorkspaceAccessMixin, self).dispatch(request, *args, **kwargs)
