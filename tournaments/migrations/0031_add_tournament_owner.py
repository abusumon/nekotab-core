# Generated migration for adding owner field to Tournament model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tournaments', '0013_scheduleevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                help_text='The user who created and owns this tournament (for payment/billing purposes)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='owned_tournaments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='owner'
            ),
        ),
    ]
