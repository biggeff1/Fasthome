import uuid
from django.conf import settings
from django.db import models

class Notification(models.Model):
    LEVELS = [('ACTION', 'Action requise'), ('INFO', 'Information'), ('SUCCESS', 'Réussite')]
    notification_id = models.CharField(max_length=40, unique=True, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    level = models.CharField(max_length=10, choices=LEVELS, default='INFO')
    title = models.CharField(max_length=200)
    message = models.TextField()
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.notification_id:
            self.notification_id = f'NTF-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)
