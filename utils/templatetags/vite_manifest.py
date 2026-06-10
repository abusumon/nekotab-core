"""
Template tag helpers for loading Vite-built assets.

Usage in templates:
    {% load vite_manifest %}
    {% vite_css "frontend/" %}
    {% vite_js "frontend/" %}
"""

import json
import os

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


def _read_manifest(out_dir: str) -> dict:
    """Read the Vite manifest.json file from the given build output directory."""
    # out_dir might be a relative path like 'frontend'; resolve it against
    # the first STATICFILES_DIR that contains a match, or STATIC_ROOT.
    manifest_path = None

    # First, look in the configured static dirs (source tree in dev/prod)
    for sf_dir in settings.STATICFILES_DIRS:
        candidate = os.path.join(sf_dir, out_dir, 'manifest.json')
        if os.path.isfile(candidate):
            manifest_path = candidate
            break

    # Fallback to STATIC_ROOT (collectstatic target)
    if manifest_path is None:
        candidate = os.path.join(settings.STATIC_ROOT, out_dir, 'manifest.json')
        if os.path.isfile(candidate):
            manifest_path = candidate

    if manifest_path is None:
        return {}

    with open(manifest_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}


@register.simple_tag
def vite_css(out_dir: str = 'frontend') -> str:
    """Return <link> tags for all CSS files referenced in the Vite manifest."""
    manifest = _read_manifest(out_dir)
    tags = []
    seen = set()

    # The manifest contains entries like:
    #   "index.html": { "css": ["assets/index-abc123.css"], ... }
    # Walk all entries and collect unique CSS files.
    for entry in manifest.values():
        for css_path in entry.get('css', []):
            if css_path not in seen:
                seen.add(css_path)
                full_url = f"{settings.STATIC_URL}{out_dir}/{css_path}"
                tags.append(
                    f'<link rel="stylesheet" href="{full_url}">'
                )

    return mark_safe('\n'.join(tags))


@register.simple_tag
def vite_js(out_dir: str = 'frontend') -> str:
    """Return <script type="module"> tags for all JS entries in the manifest."""
    manifest = _read_manifest(out_dir)
    tags = []

    # The main entry is keyed by "index.html" with its JS in the "file" field.
    for key, entry in manifest.items():
        if entry.get('isEntry') and 'file' in entry:
            js_path = entry['file']
            full_url = f"{settings.STATIC_URL}{out_dir}/{js_path}"
            tags.append(
                f'<script type="module" src="{full_url}"></script>'
            )

    return mark_safe('\n'.join(tags))