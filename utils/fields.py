from django import forms
from django.conf import settings
from django.db import models
from django.db.models import ForeignKey

# ArrayField is PostgreSQL-specific.  On non-PostgreSQL backends (e.g. SQLite
# used during local development / testing) we fall back to JSONField which
# stores the list as JSON text and is supported on all backends.
_db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
if 'postgresql' in _db_engine:
    from django.contrib.postgres.fields import ArrayField as _ArrayFieldBase
else:
    _ArrayFieldBase = None


if _ArrayFieldBase is not None:
    class ChoiceArrayField(_ArrayFieldBase):
        """
        Reference: https://gist.github.com/danni/f55c4ce19598b2b345ef
        See also: https://code.djangoproject.com/ticket/27704
        """

        def formfield(self, **kwargs):
            defaults = {
                'form_class': forms.TypedMultipleChoiceField,
                'choices': self.base_field.choices,
            }
            defaults.update(kwargs)

            # Skip our parent's formfield implementation completely as we don't
            # care for it.
            from django.contrib.postgres.fields import ArrayField
            return super(ArrayField, self).formfield(**defaults)
else:
    class ChoiceArrayField(models.JSONField):
        """SQLite-compatible fallback: stores the list as JSON.

        Accepts the same ``base_field`` constructor argument as the PostgreSQL
        ``ArrayField`` so that model definitions stay identical across backends.
        """

        def __init__(self, base_field=None, size=None, **kwargs):
            kwargs.setdefault('default', list)
            # Preserve choices from the base_field for form generation.
            self._base_field = base_field
            super().__init__(**kwargs)

        def formfield(self, **kwargs):
            if self._base_field and hasattr(self._base_field, 'choices') and self._base_field.choices:
                defaults = {
                    'form_class': forms.TypedMultipleChoiceField,
                    'choices': self._base_field.choices,
                }
                defaults.update(kwargs)
                return super().formfield(**defaults)
            return super().formfield(**kwargs)

        def deconstruct(self):
            name, path, args, kwargs = super().deconstruct()
            kwargs.pop('default', None)
            if self._base_field:
                args = [self._base_field] + list(args)
            return name, path, args, kwargs


class LabelByNameModelChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that uses `obj.name` rather than `str(obj)` for labels."""

    def label_from_instance(self, obj):
        return obj.name


class LabelByNameForeignKey(ForeignKey):
    """ForeignKey that uses `obj.name` rather than `str(obj)` for labels."""

    def formfield(self, **kwargs):
        defaults = {'form_class': LabelByNameModelChoiceField}
        defaults.update(kwargs)
        return super().formfield(**defaults)
