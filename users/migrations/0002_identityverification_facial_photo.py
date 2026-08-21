from django.db import migrations, models
import core.validators
from users.models import facial_upload_path


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='identityverification',
            name='facial_photo',
            field=models.ImageField(blank=True, null=True, upload_to=facial_upload_path, validators=[core.validators.validate_image_upload]),
        ),
    ]
