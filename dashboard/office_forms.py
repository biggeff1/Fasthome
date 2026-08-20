from django import forms
from leasing.models import Lease
from payments.models import RentInstallment

class ReceiptForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=0)
    received_at = forms.DateTimeField()
    reference = forms.CharField(required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea)

class PayoutForm(forms.Form):
    lease = forms.ModelChoiceField(queryset=Lease.objects.select_related('property').all())
    installment = forms.ModelChoiceField(queryset=RentInstallment.objects.select_related('lease').all())
    amount = forms.DecimalField(min_value=0)
    paid_at = forms.DateTimeField()
    reference = forms.CharField(required=False)
