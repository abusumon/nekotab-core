from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0033_remove_tournament_creation_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                help_text='When this tournament was created',
                null=True,
                verbose_name='created at',
            ),
        ),
    ]
