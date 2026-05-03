from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import tabbycat.campaigns.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(
                    help_text='A short label so you can recognise this image in the gallery',
                    max_length=200,
                )),
                ('image', models.ImageField(
                    help_text='JPEG, PNG, GIF or WebP — recommended width ≤ 600 px for emails',
                    upload_to=tabbycat.campaigns.models._email_image_upload_path,
                )),
                ('original_filename', models.CharField(blank=True, editable=False, max_length=255)),
                ('file_size', models.PositiveIntegerField(default=0, editable=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_images',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Uploaded Image',
                'verbose_name_plural': 'Uploaded Images',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
