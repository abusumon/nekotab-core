from django.db import models
from django.utils.translation import gettext_lazy as _

from tournaments.models import validate_dns_safe_slug


class SubdomainSlugReservation(models.Model):
    """Cross-entity slug registry guaranteeing no tournament slug collides
    with an organization workspace slug.

    Every tournament and every workspace-enabled organization gets a row in
    this table.  The unique constraint on ``slug`` prevents two entities from
    claiming the same subdomain label.
    """

    TENANT_TYPES = [
        ('tournament', 'Tournament'),
        ('organization', 'Organization'),
    ]

    slug = models.SlugField(
        unique=True,
        max_length=80,
        validators=[validate_dns_safe_slug],
        verbose_name=_("slug"),
    )
    tenant_type = models.CharField(max_length=20, choices=TENANT_TYPES)
    tournament = models.OneToOneField(
        'tournaments.Tournament', null=True, blank=True,
        on_delete=models.CASCADE, related_name='slug_reservation',
    )
    organization = models.OneToOneField(
        'organizations.Organization', null=True, blank=True,
        on_delete=models.CASCADE, related_name='slug_reservation',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(tenant_type='tournament', tournament__isnull=False, organization__isnull=True)
                    | models.Q(tenant_type='organization', tournament__isnull=True, organization__isnull=False)
                ),
                name='slug_reservation_exactly_one_target',
            ),
        ]
        verbose_name = _("subdomain slug reservation")
        verbose_name_plural = _("subdomain slug reservations")

    def __str__(self):
        return f"{self.slug} ({self.tenant_type})"
