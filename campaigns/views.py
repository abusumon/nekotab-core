import logging
import mimetypes
import re
import time
from html import unescape
from smtplib import SMTPException
from threading import Thread

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from .forms import EmailCampaignForm, TestEmailForm, CampaignAudienceForm, ImageUploadForm
from .models import EmailCampaign, CampaignRecipient, UploadedImage
from participant_crm.models import ParticipantProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Mixin that ensures only superusers can access the view."""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, _("You don't have permission to access this page."))
            return redirect('tabbycat-index')
        return redirect('login')


class CampaignListView(SuperuserRequiredMixin, ListView):
    """List all email campaigns."""
    model = EmailCampaign
    template_name = 'campaigns/campaign_list.html'
    context_object_name = 'campaigns'
    paginate_by = 20
    
    def get_queryset(self):
        return EmailCampaign.objects.all().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_subscribers'] = User.objects.filter(
            email__isnull=False
        ).exclude(email='').count()
        context['total_campaigns'] = EmailCampaign.objects.count()
        context['sent_campaigns'] = EmailCampaign.objects.filter(status='sent').count()
        return context


class CampaignCreateView(SuperuserRequiredMixin, CreateView):
    """Create a new email campaign."""
    model = EmailCampaign
    form_class = EmailCampaignForm
    template_name = 'campaigns/campaign_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Create Campaign")
        context['total_subscribers'] = User.objects.filter(
            email__isnull=False
        ).exclude(email='').count()
        context['crm_subscribers'] = ParticipantProfile.objects.filter(email_subscribed=True).count()
        if 'audience_form' not in context:
            context['audience_form'] = CampaignAudienceForm()
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        audience_form = CampaignAudienceForm(request.POST)
        if form.is_valid() and audience_form.is_valid():
            return self.form_valid(form, audience_form)
        return self.form_invalid(form, audience_form)

    def form_valid(self, form, audience_form=None):
        form.instance.created_by = self.request.user
        form.instance.status = EmailCampaign.Status.DRAFT
        response = super().form_valid(form)
        if audience_form:
            audience_form.save_audience(self.object)
        messages.success(self.request, _("Campaign created successfully! You can now preview and send it."))
        return response

    def form_invalid(self, form, audience_form=None):
        return self.render_to_response(self.get_context_data(form=form, audience_form=audience_form))
    
    def get_success_url(self):
        return reverse('campaigns:detail', kwargs={'pk': self.object.pk})


class CampaignUpdateView(SuperuserRequiredMixin, UpdateView):
    """Edit an existing email campaign."""
    model = EmailCampaign
    form_class = EmailCampaignForm
    template_name = 'campaigns/campaign_form.html'
    
    def get_queryset(self):
        # Only allow editing draft or failed campaigns
        return EmailCampaign.objects.filter(
            status__in=[EmailCampaign.Status.DRAFT, EmailCampaign.Status.FAILED]
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _("Edit Campaign")
        context['total_subscribers'] = User.objects.filter(
            email__isnull=False
        ).exclude(email='').count()
        context['crm_subscribers'] = ParticipantProfile.objects.filter(email_subscribed=True).count()
        if 'audience_form' not in context:
            context['audience_form'] = CampaignAudienceForm.from_campaign(self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        audience_form = CampaignAudienceForm(request.POST)
        if form.is_valid() and audience_form.is_valid():
            return self.form_valid(form, audience_form)
        return self.form_invalid(form, audience_form)

    def form_valid(self, form, audience_form=None):
        response = super().form_valid(form)
        if audience_form:
            audience_form.save_audience(self.object)
        messages.success(self.request, _("Campaign updated successfully!"))
        return response

    def form_invalid(self, form, audience_form=None):
        return self.render_to_response(self.get_context_data(form=form, audience_form=audience_form))
    
    def get_success_url(self):
        return reverse('campaigns:detail', kwargs={'pk': self.object.pk})


class CampaignDetailView(SuperuserRequiredMixin, DetailView):
    """View campaign details and stats."""
    model = EmailCampaign
    template_name = 'campaigns/campaign_detail.html'
    context_object_name = 'campaign'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_form'] = TestEmailForm()
        context['total_subscribers'] = User.objects.filter(
            email__isnull=False
        ).exclude(email='').count()
        context['recent_recipients'] = self.object.recipients.all()[:50]
        # Audience info
        try:
            audience = self.object.audience
            context['audience'] = audience
            context['audience_recipient_count'] = audience.recipient_count()
        except Exception:
            context['audience'] = None
            context['audience_recipient_count'] = 0
        context['crm_subscribers'] = ParticipantProfile.objects.filter(email_subscribed=True).count()
        return context


class CampaignDeleteView(SuperuserRequiredMixin, DeleteView):
    """Delete a campaign."""
    model = EmailCampaign
    template_name = 'campaigns/campaign_confirm_delete.html'
    success_url = reverse_lazy('campaigns:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Campaign deleted successfully."))
        return super().delete(request, *args, **kwargs)


class CampaignDuplicateView(SuperuserRequiredMixin, View):
    """Duplicate an existing campaign."""
    
    def post(self, request, pk):
        original = get_object_or_404(EmailCampaign, pk=pk)
        
        new_campaign = EmailCampaign.objects.create(
            name=f"{original.name} (Copy)",
            subject=original.subject,
            preview_text=original.preview_text,
            html_content=original.html_content,
            plain_text_content=original.plain_text_content,
            send_to_all=original.send_to_all,
            status=EmailCampaign.Status.DRAFT,
            created_by=request.user,
        )

        # Clone audience segment if present
        try:
            orig_audience = original.audience
            from participant_crm.models import CampaignAudience
            new_audience = CampaignAudience.objects.create(
                campaign=new_campaign,
                roles=orig_audience.roles,
                tournament_filter=orig_audience.tournament_filter,
                active_since=orig_audience.active_since,
                custom_emails=orig_audience.custom_emails,
            )
            new_audience.tag_filter.set(orig_audience.tag_filter.all())
        except Exception:
            pass
        
        messages.success(request, _("Campaign duplicated successfully!"))
        return redirect('campaigns:edit', pk=new_campaign.pk)


class CampaignPreviewView(SuperuserRequiredMixin, DetailView):
    """Preview campaign HTML in an iframe-friendly format."""
    model = EmailCampaign
    template_name = 'campaigns/campaign_preview.html'
    
    def get(self, request, *args, **kwargs):
        campaign = self.get_object()
        # Return just the HTML content for iframe preview
        from django.http import HttpResponse
        return HttpResponse(campaign.html_content, content_type='text/html')


class SendTestEmailView(SuperuserRequiredMixin, View):
    """Send a test email for preview."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk)
        form = TestEmailForm(request.POST)
        
        if form.is_valid():
            test_email = form.cleaned_data['test_email']
            
            try:
                self._send_email(campaign, test_email)
                messages.success(request, _(f"Test email sent to {test_email}!"))
            except Exception as e:
                logger.error(f"Failed to send test email: {e}", exc_info=True)
                messages.error(request, _(f"Failed to send test email: {str(e)}"))
        else:
            messages.error(request, _("Invalid email address."))
        
        return redirect('campaigns:detail', pk=pk)
    
    def _send_email(self, campaign, recipient_email):
        """Send a single email."""
        plain_text = campaign.plain_text_content
        if not plain_text:
            # Auto-generate plain text from HTML
            plain_text = strip_tags(campaign.html_content)
            plain_text = unescape(plain_text)
            plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text)
        
        email = EmailMultiAlternatives(
            subject=f"[TEST] {campaign.subject}",
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.attach_alternative(campaign.html_content, "text/html")
        email.send(fail_silently=False)


class SendCampaignView(SuperuserRequiredMixin, View):
    """Send the campaign to all subscribers or a targeted audience segment."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk)
        
        if campaign.status not in [EmailCampaign.Status.DRAFT, EmailCampaign.Status.FAILED]:
            messages.error(request, _("This campaign has already been sent."))
            return redirect('campaigns:detail', pk=pk)
        
        # Determine recipients: audience segment or legacy all-users
        recipients = self._resolve_recipients(campaign)
        
        if not recipients:
            messages.error(request, _("No subscribers to send to!"))
            return redirect('campaigns:detail', pk=pk)
        
        # Update campaign status
        campaign.status = EmailCampaign.Status.SENDING
        campaign.total_recipients = len(recipients)
        campaign.save()
        
        # Create recipient records
        CampaignRecipient.objects.filter(campaign=campaign).delete()
        recipient_objects = []
        for user_id, email in recipients:
            recipient_objects.append(CampaignRecipient(
                campaign=campaign,
                email=email,
                user_id=user_id if user_id else None,
                status=CampaignRecipient.Status.PENDING
            ))
        CampaignRecipient.objects.bulk_create(recipient_objects, ignore_conflicts=True)
        
        # Start sending in background thread
        thread = Thread(target=self._send_campaign_emails, args=(campaign.pk,))
        thread.daemon = True
        thread.start()
        
        messages.success(request, _(f"Campaign is being sent to {len(recipients)} recipients!"))
        return redirect('campaigns:detail', pk=pk)

    def _resolve_recipients(self, campaign):
        """Return list of (user_id_or_None, email) tuples for this campaign."""
        try:
            audience = campaign.audience
        except Exception:
            audience = None

        if audience:
            # Use CRM audience segment
            profiles = audience.resolve_recipients()
            result = list(profiles.values_list('user_id', 'email'))
            # Add custom emails (no user_id)
            if audience.custom_emails:
                for line in audience.custom_emails.splitlines():
                    email = line.strip()
                    if email and '@' in email:
                        result.append((None, email))
            return result
        else:
            # Legacy: all users with email
            return list(User.objects.filter(
                email__isnull=False
            ).exclude(email='').values_list('id', 'email'))
    
    def _send_campaign_emails(self, campaign_pk):
        """Background task to send all campaign emails."""
        try:
            campaign = EmailCampaign.objects.get(pk=campaign_pk)
            recipients = campaign.recipients.filter(status=CampaignRecipient.Status.PENDING)
            
            plain_text = campaign.plain_text_content
            if not plain_text:
                plain_text = strip_tags(campaign.html_content)
                plain_text = unescape(plain_text)
                plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text)
            
            successful = 0
            failed = 0
            
            for recipient in recipients:
                try:
                    email = EmailMultiAlternatives(
                        subject=campaign.subject,
                        body=plain_text,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[recipient.email],
                    )
                    email.attach_alternative(campaign.html_content, "text/html")
                    email.send(fail_silently=False)
                    
                    recipient.status = CampaignRecipient.Status.SENT
                    recipient.sent_at = timezone.now()
                    successful += 1
                    
                except Exception as e:
                    recipient.status = CampaignRecipient.Status.FAILED
                    recipient.error_message = str(e)
                    failed += 1
                    logger.error(f"Failed to send to {recipient.email}: {e}")
                
                recipient.save()
                
                # Rate limiting: Resend free tier allows max 2 emails/second
                # Wait 0.6 seconds between emails to stay under the limit
                time.sleep(0.6)
            
            # Update campaign stats
            campaign.successful_sends = successful
            campaign.failed_sends = failed
            campaign.status = EmailCampaign.Status.SENT
            campaign.sent_at = timezone.now()
            campaign.save()
            
        except Exception as e:
            logger.error(f"Campaign sending failed: {e}", exc_info=True)
            try:
                campaign = EmailCampaign.objects.get(pk=campaign_pk)
                campaign.status = EmailCampaign.Status.FAILED
                campaign.save()
            except:
                pass


class CampaignStatsAPIView(SuperuserRequiredMixin, View):
    """API endpoint for real-time campaign stats."""
    
    def get(self, request, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk)
        return JsonResponse({
            'status': campaign.status,
            'status_display': campaign.get_status_display(),
            'total_recipients': campaign.total_recipients,
            'successful_sends': campaign.successful_sends,
            'failed_sends': campaign.failed_sends,
            'success_rate': campaign.success_rate,
        })


class RetryFailedEmailsView(SuperuserRequiredMixin, View):
    """Retry sending emails to recipients that previously failed."""
    
    def post(self, request, pk):
        campaign = get_object_or_404(EmailCampaign, pk=pk)
        
        # Get failed recipients
        failed_recipients = campaign.recipients.filter(
            status=CampaignRecipient.Status.FAILED
        )
        
        failed_count = failed_recipients.count()
        if failed_count == 0:
            messages.info(request, _("No failed recipients to retry."))
            return redirect('campaigns:detail', pk=pk)
        
        # Reset failed recipients to pending
        failed_recipients.update(
            status=CampaignRecipient.Status.PENDING,
            error_message=''
        )
        
        # Update campaign status
        campaign.status = EmailCampaign.Status.SENDING
        campaign.save()
        
        # Start sending in background thread
        thread = Thread(target=self._retry_failed_emails, args=(campaign.pk,))
        thread.daemon = True
        thread.start()
        
        messages.success(request, _(f"Retrying {failed_count} failed emails..."))
        return redirect('campaigns:detail', pk=pk)
    
    def _retry_failed_emails(self, campaign_pk):
        """Background task to retry failed emails."""
        try:
            campaign = EmailCampaign.objects.get(pk=campaign_pk)
            recipients = campaign.recipients.filter(status=CampaignRecipient.Status.PENDING)
            
            plain_text = campaign.plain_text_content
            if not plain_text:
                plain_text = strip_tags(campaign.html_content)
                plain_text = unescape(plain_text)
                plain_text = re.sub(r'\n\s*\n', '\n\n', plain_text)
            
            new_successful = 0
            new_failed = 0
            
            for recipient in recipients:
                try:
                    email = EmailMultiAlternatives(
                        subject=campaign.subject,
                        body=plain_text,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[recipient.email],
                    )
                    email.attach_alternative(campaign.html_content, "text/html")
                    email.send(fail_silently=False)
                    
                    recipient.status = CampaignRecipient.Status.SENT
                    recipient.sent_at = timezone.now()
                    recipient.error_message = ''
                    new_successful += 1
                    
                except Exception as e:
                    recipient.status = CampaignRecipient.Status.FAILED
                    recipient.error_message = str(e)
                    new_failed += 1
                    logger.error(f"Failed to send to {recipient.email}: {e}")
                
                recipient.save()
                
                # Rate limiting: Wait 0.6 seconds between emails
                time.sleep(0.6)
            
            # Update campaign stats
            campaign.successful_sends += new_successful
            campaign.failed_sends = new_failed
            campaign.status = EmailCampaign.Status.SENT
            campaign.save()
            
        except Exception as e:
            logger.error(f"Retry sending failed: {e}", exc_info=True)


# ==============================================================================
# Image Gallery (superuser only) + public serve view
# ==============================================================================

class ImageGalleryView(SuperuserRequiredMixin, ListView):
    """Superuser-only gallery: list all uploaded images and show upload form."""
    model = UploadedImage
    template_name = 'campaigns/image_gallery.html'
    context_object_name = 'images'
    paginate_by = 24

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['upload_form'] = ImageUploadForm()
        return context


class ImageUploadView(SuperuserRequiredMixin, View):
    """Handle image upload (POST only)."""

    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, _('Upload failed: ') + str(form.errors.as_text()))
            return redirect('campaigns:image-gallery')

        img = form.save(commit=False)
        img.uploaded_by = request.user
        uploaded_file = request.FILES['image']
        img.original_filename = uploaded_file.name
        img.file_size = uploaded_file.size
        img.save()

        public_url = request.build_absolute_uri(
            reverse('image-serve', kwargs={'pk': img.pk})
        )
        messages.success(
            request,
            _('Image uploaded! Copy this URL for your emails: ') + public_url,
        )
        return redirect('campaigns:image-gallery')


class ImageDeleteView(SuperuserRequiredMixin, View):
    """Delete an uploaded image (POST only)."""

    def post(self, request, pk):
        img = get_object_or_404(UploadedImage, pk=pk)
        # Delete the underlying file from storage
        img.image.delete(save=False)
        img.delete()
        messages.success(request, _('Image deleted.'))
        return redirect('campaigns:image-gallery')


def serve_image(request, pk):
    """
    Public view — anyone with the URL can view the image.
    No authentication required (images are referenced in emails sent to the public).
    """
    img = get_object_or_404(UploadedImage, pk=pk)
    img_url = img.image.url

    # Cloud storage (Cloudinary, S3) returns an absolute https:// URL
    if img_url.startswith('http://') or img_url.startswith('https://'):
        return HttpResponseRedirect(img_url)

    # Local / volume storage — serve the file directly
    content_type, _ = mimetypes.guess_type(img.image.name)
    if not content_type:
        content_type = 'image/jpeg'
    try:
        return FileResponse(img.image.open('rb'), content_type=content_type)
    except (FileNotFoundError, OSError):
        raise Http404('Image file not found')
