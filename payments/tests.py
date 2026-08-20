from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from leasing.models import Lease, RentalCase
from properties.models import Property, PropertyType
from users.models import User
from visits.models import VisitRequest
from .models import LandlordPayout, PaymentReceipt, RentInstallment


class PaymentInvariantTests(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            email='landlord@example.com',
            password='A-secure-password-123',
            phone='+243900000101',
            last_name='Landlord',
            first_name='Test',
        )
        self.tenant = User.objects.create_user(
            email='tenant@example.com',
            password='A-secure-password-123',
            phone='+243900000102',
            last_name='Tenant',
            first_name='Test',
        )
        property_type = PropertyType.objects.create(name='Appartement')
        self.property = Property.objects.create(
            owner=self.landlord,
            property_type=property_type,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            neighborhood='Golf',
            bedroom_count=2,
            living_room_count=1,
            max_occupants=4,
            monthly_rent=Decimal('300000'),
            status='RENTED',
        )
        self.visit = VisitRequest.objects.create(
            property=self.property,
            requester=self.tenant,
            requested_date=date.today(),
            fasthome_approved=True,
            landlord_approved=True,
            status='COMPLETED',
        )
        self.case = RentalCase.objects.create(
            property=self.property,
            tenant=self.tenant,
            visit=self.visit,
            status='CONTRACTING',
        )
        self.lease = Lease.objects.create(
            rental_case=self.case,
            property=self.property,
            tenant=self.tenant,
            landlord=self.landlord,
            monthly_rent=Decimal('300000'),
            status='ACTIVE',
        )
        self.installment = RentInstallment.objects.create(
            lease=self.lease,
            due_date=date.today(),
            amount_due=Decimal('300000'),
        )

    def _user(self):
        return self.landlord

    def test_payment_can_be_split_into_multiple_tranches(self):
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('100000'),
            received_at='2026-08-20T10:00:00Z',
            recorded_by=self._user(),
        )
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('200000'),
            received_at='2026-08-20T11:00:00Z',
            recorded_by=self._user(),
        )
        self.installment.refresh_from_db()
        self.assertEqual(self.installment.total_received(), Decimal('300000'))

    def test_payment_cannot_exceed_due_amount(self):
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('250000'),
            received_at='2026-08-20T10:00:00Z',
            recorded_by=self._user(),
        )
        with self.assertRaises(ValidationError):
            PaymentReceipt.objects.create(
                lease=self.lease,
                installment=self.installment,
                amount=Decimal('60000'),
                received_at='2026-08-20T11:00:00Z',
                recorded_by=self._user(),
            )

    def test_payment_must_be_positive(self):
        for amount in (Decimal('0'), Decimal('-1')):
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    PaymentReceipt.objects.create(
                        lease=self.lease,
                        installment=self.installment,
                        amount=amount,
                        received_at='2026-08-20T10:00:00Z',
                        recorded_by=self._user(),
                    )

    def test_payment_installment_must_belong_to_lease(self):
        other_installment = RentInstallment.objects.create(
            lease=Lease.objects.create(
                rental_case=RentalCase.objects.create(
                    property=self.property,
                    tenant=self.tenant,
                    visit=VisitRequest.objects.create(
                        property=self.property,
                        requester=self.tenant,
                        requested_date=date.today(),
                        fasthome_approved=True,
                        landlord_approved=True,
                        status='COMPLETED',
                    ),
                    status='CONTRACTING',
                ),
                property=self.property,
                tenant=self.tenant,
                landlord=self.landlord,
                monthly_rent=Decimal('300000'),
                status='ACTIVE',
            ),
            due_date=date.today(),
            amount_due=Decimal('300000'),
        )
        with self.assertRaises(ValidationError):
            PaymentReceipt.objects.create(
                lease=self.lease,
                installment=other_installment,
                amount=Decimal('1000'),
                received_at='2026-08-20T10:00:00Z',
                recorded_by=self._user(),
            )

    def test_payout_cannot_exceed_amount_received(self):
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('150000'),
            received_at='2026-08-20T10:00:00Z',
            recorded_by=self._user(),
        )
        with self.assertRaises(ValidationError):
            LandlordPayout.objects.create(
                lease=self.lease,
                installment=self.installment,
                amount=Decimal('150001'),
                paid_at='2026-08-20T12:00:00Z',
                recorded_by=self._user(),
            )

    def test_payout_can_be_split_and_cannot_exceed_remaining_received_balance(self):
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('300000'),
            received_at='2026-08-20T10:00:00Z',
            recorded_by=self._user(),
        )
        LandlordPayout.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('100000'),
            paid_at='2026-08-20T12:00:00Z',
            recorded_by=self._user(),
        )
        LandlordPayout.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('200000'),
            paid_at='2026-08-20T13:00:00Z',
            recorded_by=self._user(),
        )
        self.assertEqual(self.installment.total_paid_to_landlord(), Decimal('300000'))
        self.assertEqual(self.installment.remaining_to_pay_out(), Decimal('0'))

    def test_payout_must_be_positive(self):
        PaymentReceipt.objects.create(
            lease=self.lease,
            installment=self.installment,
            amount=Decimal('100000'),
            received_at='2026-08-20T10:00:00Z',
            recorded_by=self._user(),
        )
        for amount in (Decimal('0'), Decimal('-1')):
            with self.subTest(amount=amount):
                with self.assertRaises(ValidationError):
                    LandlordPayout.objects.create(
                        lease=self.lease,
                        installment=self.installment,
                        amount=amount,
                        paid_at='2026-08-20T12:00:00Z',
                        recorded_by=self._user(),
                    )
