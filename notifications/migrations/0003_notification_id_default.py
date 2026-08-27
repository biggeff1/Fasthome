from django.db import migrations
import uuid


def ensure_notification_ids(apps, schema_editor):
    NotificationModel = apps.get_model("notifications", "Notification")
    for notification in NotificationModel.objects.filter(notification_id__isnull=True):
        notification.notification_id = f"NTF-{uuid.uuid4().hex[:10].upper()}"
        notification.save(update_fields=["notification_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(ensure_notification_ids, migrations.RunPython.noop),
    ]
