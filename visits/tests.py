from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from properties.models import Property, PropertyPublication, PropertyType
from users.models import User
from .models import VisitRequest


class VisitWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner-visit@example.com', password='A-secure-password-123',
            phone='+243900000201', last_name='Owner', first_name='Visit',
        )
        self.tenant = User.objects.create_user(
            email='tenant-visit@example.com', password='A-secure-password-123',
            phone='+243900000202', last_name='Tenant', first_name='Visit',
        )
        self.tenant.is_certified = True
        self.tenant.save(update_fields=['is_certified'])
        self.outsider = User.objects.create_user(
            email='outsider-visit@example.com', password='A-secure-password-123',
            phone='+243900000203', last_name='Outside', first_name='Visit',
        )
        property_type = PropertyType.objects.create(name='Maison visite')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type,
            furnished=False, province='Haut-Katanga', city_or_territory='Lubumbashi',
            administrative_subdivision='Commune', neighborhood='Golf',
            bedroom_count=2, living_room_count=1, max_occupants=4,
            monthly_rent=Decimal('300000'), status='AVAILABLE',
        )
        PropertyPublication.objects.create(property=self.property, status='PUBLISHED')

    def test_request_visit_is_post_only_and_does_not_expose_requester_to_owner(self):
        self.client.force_login(self.tenant)
        response = self.client.post(reverse('request_visit', args=[self.property.property_id]), {
            'requested_date': (date.today() + timedelta(days=2)).isoformat(),
            'requested_time_slot': '10:00-12:00',
        })
        self.assertEqual(response.status_code, 302)
        visit = VisitRequest.objects.get(property=self.property)
        self.assertEqual(visit.requester_id, self.tenant.id)
        self.assertFalse(visit.landlord_approved)

    def test_tenant_can_choose_take_only_after_completed_visit(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant,
            requested_date=date.today() + timedelta(days=1),
            fasthome_approved=True, landlord_approved=True, status='CONFIRMED',
        )
        self.client.force_login(self.tenant)
        before = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(before.status_code, 302)
        self.assertFalse(hasattr(visit, 'rental_case'))
        visit.status = 'COMPLETED'
        visit.save(update_fields=['status'])
        response = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(visit.rental_case)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'UNDER_REVIEW')

    def test_outsider_cannot_make_tenant_decision(self):
        visit = VisitRequest.objects.create(
            property=self.property, requester=self.tenant,
            requested_date=date.today() + timedelta(days=1), status='COMPLETED',
        )
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('tenant_decision', args=[visit.visit_id]), {'action': 'take'})
        self.assertEqual(response.status_code, 404)
