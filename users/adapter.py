from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class NekotabAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_authenticated and request.user.is_superuser:
            return reverse('analytics:owner_dashboard')
        return super().get_login_redirect_url(request)
