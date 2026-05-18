from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prereg', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='preregform',
            name='responses_visibility',
            field=models.CharField(
                choices=[
                    ('public', 'Public — anyone can view the slots page'),
                    ('private_link', 'Private link — only people with the secret link'),
                    ('admin_only', 'Admin only — slots page hidden from public'),
                ],
                default='public',
                help_text='Controls who can view the public slot allocation results page.',
                max_length=20,
                verbose_name='results visibility',
            ),
        ),
    ]
