from decimal import Decimal

from django import forms
from django.utils import timezone

from leasing.models import Lease
from payments.models import RentInstallment
from payments.models import PaymentReceipt, LandlordPayout


class ReceiptForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2)
    received_at = forms.DateTimeField(initial=timezone.now)
    reference = forms.CharField(required=False, max_length=100)
    notes = forms.CharField(required=False, max_length=2000, widget=forms.Textarea)

    def clean(self):
        cleaned = super().clean()
        lease = cleaned.get('lease')
        installment = cleaned.get('installment')
        amount = cleaned.get('amount')
        if lease and installment and installment.lease_id != lease.id:
            raise forms.ValidationError('La location et l’échéance ne correspondent pas.')
        if installment and amount:
            already_received = sum((p.amount for p in PaymentReceipt.objects.filter(installment=installment)), Decimal('0'))
            if already_received + amount > installment.amount_due:
                raise forms.ValidationError('Le paiement dépasse le solde restant de cette échéance.')
        return cleaned


class PayoutForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2)
    paid_at = forms.DateTimeField(initial=timezone.now)
    reference = forms.CharField(required=False, max_length=100)

    def clean(self):
        cleaned = super().clean()
        lease = cleaned.get('lease')
        installment = cleaned.get('installment')
        amount = cleaned.get('amount')
        if lease and installment and installment.lease_id != lease.id:
            raise forms.ValidationError('La location et l’échéance ne correspondent pas.')
        if installment and amount:
            received = sum((p.amount for p in PaymentReceipt.objects.filter(installment=installment)), Decimal('0'))
            already_paid = sum((p.amount for p in LandlordPayout.objects.filter(installment=installment)), Decimal('0'))
            if already_paid + amount > received:
                raise forms.ValidationError('Le versement au bailleur ne peut pas dépasser les montants réellement reçus par Fasthome.')
        return cleaned
