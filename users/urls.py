from django.contrib.auth.views import LoginView
from django.urls import include, path

from .forms import PublicLoginForm
from .views import ActivateAccountView, PublicSignupView

urlpatterns = [
    path('login/', LoginView.as_view(
        authentication_form=PublicLoginForm,
        template_name='registration/login.html',
    ), name='login'),
    path('', include('django.contrib.auth.urls')),
    path('signup/', PublicSignupView.as_view(), name='signup'),
    path('verify/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate-account'),
]
