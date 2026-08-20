import uuid
from django.db import models

class Contract(models.Model):
    TYPES = [('TENANT', 'Sofasthome - Locataire'), ('LANDLORD', 'Sofasthome - Bailleur')]
    STATUS = [('PENDING', 'En attente'), ('SIGNED', 'Signé'), ('UPLOADED', 'Téléversé'), ('VALIDATED', 'Validé'), ('REJECTED', 'Rejeté')]
    contract_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='contracts')
    contract_type = models.CharField(max_length=10, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    signed_document = models.FileField(upload_to='private/contracts/', null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True, blank=True, related_name='uploaded_contracts')
    def save(self, *args, **kwargs):
        if not self.contract_id:
            prefix = 'FCL' if self.contract_type == 'TENANT' else 'FCB'
            self.contract_id = f'{prefix}-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)
