from django.db import migrations, models
import notifications.models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_id',
            field=models.CharField(
                default=notifications.models.generate_notification_id,
                editable=False,
                max_length=40,
                unique=True,
            ),
        ),
    ]
