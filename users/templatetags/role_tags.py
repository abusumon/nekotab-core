from django import template

from ..groups import describe_role
from ..permissions import Permission

register = template.Library()


@register.simple_tag
def role_info(group):
    """Plain-language summary of a tournament role, for the invite page."""
    summary, preset = describe_role(group)
    labels = []
    for value in group.permissions or []:
        try:
            labels.append(str(Permission(value).label))
        except ValueError:
            pass
    return {'summary': summary, 'full': preset == 'TabDirector', 'labels': sorted(labels)}
