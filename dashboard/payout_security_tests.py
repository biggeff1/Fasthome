from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from leasing.models import Lease
from payments.models import LandlordPayout, PaymentReceipt, RentInstallment
from properties.models import Property, PropertyType
from users.models import User


class PayoutConcurrencySecurityTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email='payout-staff@example.com', password='A-secure-password-123',
            phone='+243900001231', is_staff=True,
        )
        self.landlord = User.objects.create_user(
            email='payout-landlord@example.com', password='A-secure-password-123',
            phone='+243900001232',
        )
        self.tenant = User.objects.create_user(
            email='payout-tenant@example.com', password='A-secure-password-123',
            phone='+243900001233',
        )
        property_type = PropertyType.objects.create(name='Payout test type')
        prop = Property.objects.create(
            owner=self.landlord, property_type=property_type, title='Payout test property',
            status='RENTED', monthly_rent=Decimal('100'),
        )
        self.lease = Lease.objects.create(
            property=prop, tenant=self.tenant, landlord=self.landlord,
            monthly_rent=Decimal('100'), status='ACTIVE',
        )
        self.installment = RentInstallment.objects.create(
            lease=self.lease, amount_due=Decimal('100'), amount_received=Decimal('100'),
            due_date='2026-08-24', status='PAID',
        )
        PaymentReceipt.objects.create(
            installment=self.installment, amount=Decimal('100'), received_by=self.staff,
            reference='TEST-RECEIPT',
        )

    def test_payout_view_rechecks_remaining_balance_inside_transaction(self):
        LandlordPayout.objects.create(
            installment=self.installment, amount=Decimal('60'), paid_by=self.staff,
            reference='FIRST-PAYOUT',
        )
        self.client.force_login(self.staff)
        response = self.client.post(reverse('office_payout'), {
            'lease': self.lease.pk,
            'installment': self.installment.pk,
            'amount': '41.00',
            'paid_at': '2026-08-24 12:00:00',
            'reference': 'SECOND-PAYOUT',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LandlordPayout.objects.filter(reference='SECOND-PAYOUT').exists())
