from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.utils.html import escape
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django import forms
import time

from .models import Article, ArticleCategory


# ============================================================
# Learn Hub
# ============================================================

class LearnHubView(ListView):
    """Content hub listing published articles by category."""
    model = Article
    template_name = 'content/learn_hub.html'
    context_object_name = 'articles'

    def get_queryset(self):
        qs = Article.objects.filter(status=Article.Status.PUBLISHED).select_related('category')
        category_slug = self.request.GET.get('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = ArticleCategory.objects.all()
        ctx['active_category'] = self.request.GET.get('category', '')
        ctx['page_title'] = 'Learn Debate'
        ctx['seo_keywords'] = 'debate guides, parliamentary debate, BP debate, debate formats, judging debate'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/learn/"
        return ctx


class ArticleDetailView(DetailView):
    """Single article / stub page."""
    model = Article
    template_name = 'content/article_detail.html'
    context_object_name = 'article'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Show drafts only to superusers (preview mode)
        qs = Article.objects.select_related('category')
        if not self.request.user.is_superuser:
            qs = qs.filter(status=Article.Status.PUBLISHED)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.object
        ctx['page_title'] = article.seo_title
        ctx['meta_description'] = article.seo_description
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}{article.get_absolute_url()}"
        ctx['noindex'] = not article.is_indexable
        # Related articles in same category
        if article.category:
            ctx['related_articles'] = (
                Article.objects
                .filter(category=article.category, status=Article.Status.PUBLISHED)
                .exclude(pk=article.pk)[:4]
            )
        return ctx


# ============================================================
# Trust / Legal Pages
# ============================================================

class AboutView(TemplateView):
    template_name = 'legal/about.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'About NekoTab'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/about/"
        return ctx


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea, max_length=5000)
    # Honeypot field — bots fill this, humans don't
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    # Timestamp anti-bot check
    form_loaded_at = forms.FloatField(widget=forms.HiddenInput())

    def clean_website(self):
        """Honeypot: if filled, it's a bot."""
        if self.cleaned_data.get('website'):
            raise forms.ValidationError("Bot detected.")
        return ''

    def clean_form_loaded_at(self):
        """Reject submissions faster than 3 seconds (bot behavior)."""
        loaded_at = self.cleaned_data.get('form_loaded_at', 0)
        if time.time() - loaded_at < 3:
            raise forms.ValidationError("Submission too fast.")
        return loaded_at


class ContactView(FormView):
    template_name = 'legal/contact.html'
    form_class = ContactForm
    success_url = '/contact/?sent=1'

    def get_initial(self):
        return {'form_loaded_at': time.time()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Contact Us'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/contact/"
        ctx['message_sent'] = self.request.GET.get('sent') == '1'
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            send_mail(
                subject=f"[NekoTab Contact] {d['subject']}",
                message=f"From: {escape(d['name'])} <{d['email']}>\n\n{escape(d['message'])}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['support@nekotab.app'],
                fail_silently=True,
            )
        except Exception:
            pass  # Fail silently — log via Sentry in production
        return super().form_valid(form)


class PrivacyView(TemplateView):
    template_name = 'legal/privacy.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Privacy Policy'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/privacy/"
        return ctx


class TermsView(TemplateView):
    template_name = 'legal/terms.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Terms of Service'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/terms/"
        return ctx


class DisclaimerView(TemplateView):
    template_name = 'legal/disclaimer.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Disclaimer'
        ctx['canonical_url'] = f"{getattr(settings, 'SITE_BASE_URL', 'https://nekotab.app')}/disclaimer/"
        return ctx
