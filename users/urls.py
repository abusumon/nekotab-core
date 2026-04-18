from django.contrib.auth.views import LoginView, PasswordResetView
from django.urls import include, path

from .forms import PublicLoginForm, PublicPasswordResetForm
from .views import ActivateAccountView, PublicSignupView

urlpatterns = [
    path('login/', LoginView.as_view(
        authentication_form=PublicLoginForm,
        template_name='registration/login.html',
    ), name='login'),
    path('password_reset/', PasswordResetView.as_view(
        form_class=PublicPasswordResetForm,
    ), name='password_reset'),
    path('', include('django.contrib.auth.urls')),
    path('signup/', PublicSignupView.as_view(), name='signup'),
    path('verify/<uidb64>/<token>/', ActivateAccountView.as_view(), name='activate-account'),
]
