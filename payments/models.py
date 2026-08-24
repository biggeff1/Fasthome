from calendar import monthrange
from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction


class RentInstallment(models.Model):
    STATUS = [
        ('UPCOMING', 'À venir'),
        ('PARTIAL', 'Partiellement payé'),
        ('PAID', 'Payé'),
        ('LATE', 'En retard'),
        ('REGULARIZED', 'Régularisé'),
    ]
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='installments')
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='UPCOMING')

    def total_received(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal('0'))

    def total_paid_to_landlord(self):
        return sum((payout.amount for payout in self.payouts.all()), Decimal('0'))

    def remaining_to_receive(self):
        return max(self.amount_due - self.total_received(), Decimal('0'))

    def remaining_to_pay_out(self):
        return max(self.total_received() - self.total_paid_to_landlord(), Decimal('0'))

    def refresh_payment_status(self):
        total = self.total_received()
        if total >= self.amount_due:
            new_status = 'PAID'
        elif total > 0:
            new_status = 'PARTIAL'
        else:
            new_status = self.status if self.status == 'LATE' else 'UPCOMING'
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])
        return self.status

    def next_due_date(self):
        year = self.due_date.year + (1 if self.due_date.month == 12 else 0)
        month = 1 if self.due_date.month == 12 else self.due_date.month + 1
        return self.due_date.replace(year=year, month=month, day=min(self.due_date.day, monthrange(year, month)[1]))

    def ensure_next_installment(self):
        if self.total_received() < self.amount_due:
            return None
        installment, _ = RentInstallment.objects.get_or_create(
            lease=self.lease,
            due_date=self.next_due_date(),
            defaults={'amount_due': self.lease.monthly_rent, 'status': 'UPCOMING'},
        )
        return installment


class PaymentReceipt(models.Model):
    payment_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='payment_receipts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    received_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_receipts')
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Le montant reçu doit être supérieur à zéro.'})
        if self.installment_id and self.lease_id and self.installment.lease_id != self.lease_id:
            raise ValidationError({'installment': 'L’échéance sélectionnée n’appartient pas à cette location.'})
        if self.pk:
            return
        if self.installment_id and self.amount + self.installment.total_received() > self.installment.amount_due:
            raise ValidationError({'amount': 'Le montant reçu dépasse le solde de l’échéance.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.installment_id:
                self.installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            self.full_clean()
            if not self.payment_id:
                self.payment_id = f'PAY-{uuid.uuid4().hex[:10].upper()}'
            super().save(*args, **kwargs)
            installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            installment.refresh_payment_status()
            if installment.status == 'PAID':
                installment.ensure_next_installment()


class LandlordPayout(models.Model):
    payout_id = models.CharField(max_length=40, unique=True, editable=False)
    lease = models.ForeignKey('leasing.Lease', on_delete=models.PROTECT, related_name='landlord_payouts')
    installment = models.ForeignKey(RentInstallment, on_delete=models.PROTECT, related_name='payouts')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_at = models.DateTimeField()
    recorded_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='recorded_payouts')
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='PAID')

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': 'Le montant versé doit être supérieur à zéro.'})
        if self.installment_id and self.lease_id and self.installment.lease_id != self.lease_id:
            raise ValidationError({'installment': 'L’échéance sélectionnée n’appartient pas à cette location.'})
        if self.pk:
            return
        if self.installment_id and self.amount + self.installment.total_paid_to_landlord() > self.installment.total_received():
            raise ValidationError({'amount': 'Le versement dépasse le montant réellement reçu par Fasthome.'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.installment_id:
                self.installment = RentInstallment.objects.select_for_update().get(pk=self.installment_id)
            self.full_clean()
            if not self.payout_id:
                self.payout_id = f'PAY-OUT-{uuid.uuid4().hex[:10].upper()}'
            super().save(*args, **kwargs)
