import uuid
from django.db import models

class RentInstallment(models.Model):
    STATUS = [('UPCOMING', 'À venir'), ('PARTIAL', 'Partiellement payé'), ('PAID', 'Payé'), ('LATE', 'En retard'), ('REGULARIZED', 'Régularisé')]
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='installments')
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='UPCOMING')

class PaymentReceipt(models.Model):
    payment_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='payment_receipts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    received_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_receipts')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f'PAY-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

class LandlordPayout(models.Model):
    payout_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='landlord_payouts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_payouts')
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='PAID')
    def save(self, *args, **kwargs):
        if not self.payout_id:
            self.payout_id = f'PAY-OUT-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)
