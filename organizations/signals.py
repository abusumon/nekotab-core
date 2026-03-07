"""Signals for the organizations app.

Handles permission cache invalidation when org membership changes to prevent
stale authorization decisions after role changes or membership revocation.
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Versioned permission cache
#
# Strategy:
#   - Each user has a permission cache version:  perm_version:{user_id}
#   - Permission cache keys include the version:
#       user_{id}_{slug}_{perm}_{version}_permission
#   - When membership changes, we increment the version, which naturally
#     invalidates all stale cache entries without needing to enumerate them.
# ---------------------------------------------------------------------------

PERM_VERSION_KEY = "perm_version:%d"


def get_perm_cache_version(user_id):
    """Return the current permission cache version for a user.

    If no version exists, initialise to 1.
    """
    version = cache.get(PERM_VERSION_KEY % user_id)
    if version is None:
        cache.set(PERM_VERSION_KEY % user_id, 1, timeout=None)
        return 1
    return version


def bump_perm_cache_version(user_id):
    """Increment the permission cache version, invalidating all cached perms."""
    key = PERM_VERSION_KEY % user_id
    try:
        new_version = cache.incr(key)
    except ValueError:
        # Key doesn't exist yet — initialise it
        cache.set(key, 2, timeout=None)
        new_version = 2
    logger.info("Permission cache version bumped for user %d -> v%d", user_id, new_version)
    return new_version


def _invalidate_tournament_caches_for_org(organization_id):
    """Invalidate tournament object caches for all tournaments in an org.

    This ensures the middleware picks up fresh tournament objects after org
    membership changes.
    """
    # Lazy import to avoid circular imports
    from tournaments.models import Tournament
    slugs = Tournament.objects.filter(
        organization_id=organization_id,
    ).values_list('slug', flat=True)
    for slug in slugs:
        cache.delete(f"{slug}_object")


@receiver(post_save, sender='organizations.OrganizationMembership')
def invalidate_perms_on_membership_save(sender, instance, **kwargs):
    """When a membership is created or updated (role change), invalidate
    the user's permission cache so changes take effect immediately."""
    bump_perm_cache_version(instance.user_id)
    _invalidate_tournament_caches_for_org(instance.organization_id)
    logger.debug(
        "Membership save: user=%d org=%d role=%s",
        instance.user_id, instance.organization_id, instance.role,
    )


@receiver(post_delete, sender='organizations.OrganizationMembership')
def invalidate_perms_on_membership_delete(sender, instance, **kwargs):
    """When a membership is deleted (user removed from org), invalidate
    their permission cache so access is revoked immediately."""
    bump_perm_cache_version(instance.user_id)
    _invalidate_tournament_caches_for_org(instance.organization_id)
    logger.debug(
        "Membership deleted: user=%d org=%d",
        instance.user_id, instance.organization_id,
    )


# ---------------------------------------------------------------------------
# Subdomain slug reservation sync
# ---------------------------------------------------------------------------

@receiver(post_save, sender='organizations.Organization')
def sync_org_slug_reservation(sender, instance, **kwargs):
    """Create or remove a SubdomainSlugReservation when an organization
    is saved, depending on whether workspace mode is enabled."""
    from core.models import SubdomainSlugReservation
    if instance.is_workspace_enabled:
        SubdomainSlugReservation.objects.get_or_create(
            slug=instance.slug.lower(),
            defaults={
                'tenant_type': 'organization',
                'organization': instance,
            },
        )
    else:
        # Workspace disabled — remove any existing reservation for this org
        SubdomainSlugReservation.objects.filter(
            organization=instance, tenant_type='organization',
        ).delete()


# ---------------------------------------------------------------------------
# Tenant cache invalidation (for SubdomainTenantMiddleware)
# ---------------------------------------------------------------------------

@receiver(post_save, sender='organizations.Organization')
def invalidate_tenant_cache_on_org_save(sender, instance, **kwargs):
    """Bust tenant resolution caches when an organization is saved."""
    cache.delete(f"tenant_type_{instance.slug}")
    cache.delete(f"tenant_type_{instance.slug.lower()}")
    cache.delete(f"org_obj_{instance.slug}")
    cache.delete(f"org_obj_{instance.slug.lower()}")


@receiver(post_delete, sender='organizations.Organization')
def invalidate_tenant_cache_on_org_delete(sender, instance, **kwargs):
    """Bust tenant resolution caches when an organization is deleted."""
    cache.delete(f"tenant_type_{instance.slug}")
    cache.delete(f"tenant_type_{instance.slug.lower()}")
    cache.delete(f"org_obj_{instance.slug}")
    cache.delete(f"org_obj_{instance.slug.lower()}")
