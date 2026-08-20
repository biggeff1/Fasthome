import uuid
from django.conf import settings
from django.db import models

class RentalCase(models.Model):
    STATUS = [('OPEN', 'Ouvert'), ('UNDER_REVIEW', 'En vérification'), ('ACCEPTED', 'Accepté'), ('CONTRACTING', 'Contractualisation'), ('OFFICIAL', 'Officiel'), ('REJECTED', 'Refusé'), ('CLOSED', 'Clôturé')]
    case_id = models.CharField(max_length=32, unique=True, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='rental_cases')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='rental_cases_as_tenant')
    visit = models.OneToOneField('visits.VisitRequest', on_delete=models.PROTECT, related_name='rental_case')
    status = models.CharField(max_length=20, choices=STATUS, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.case_id:
            self.case_id = f'DOS-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

class Lease(models.Model):
    STATUS = [('PENDING', 'En attente'), ('ACTIVE', 'Active'), ('RENEWAL', 'Renouvellement'), ('TERMINATION', 'Résiliation'), ('CLOSED', 'Clôturée')]
    lease_id = models.CharField(max_length=32, unique=True, editable=False)
    rental_case = models.OneToOneField(RentalCase, on_delete=models.PROTECT, related_name='lease')
    property = models.ForeignKey('properties.Property', on_delete=models.PROTECT, related_name='leases')
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leases_as_tenant')
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='leases_as_landlord')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=14, decimal_places=2)
    guarantee_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.lease_id:
            self.lease_id = f'FL-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)
