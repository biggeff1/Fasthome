from django.db import IntegrityError
from django.test import TestCase

from users.models import User

from .models import Property, PropertyType


class PropertyTypeSeedTests(TestCase):
    def test_default_property_types_are_available_for_publication(self):
        expected = [
            'Maison',
            'Appartement',
            'Studio',
            'Chambre',
            'Duplex',
            'Villa',
            'Autre',
        ]

        self.assertEqual(
            list(
                PropertyType.objects.filter(active=True)
                .order_by('order')
                .values_list('name', flat=True)
            ),
            expected,
        )


class PropertyServiceConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='property-tests@example.com',
            password='A-secure-password-123',
            phone='+243900001001',
            last_name='Property',
            first_name='Test',
        )
        self.property_type = PropertyType.objects.create(name='Maison test')

    def make_property(self, **overrides):
        data = {
            'owner': self.user,
            'property_type': self.property_type,
            'province': 'Haut-Katanga',
            'city_or_territory': 'Lubumbashi',
        }
        data.update(overrides)
        return Property(**data)

    def test_service_availability_accepts_zero_to_seven_days(self):
        property_obj = self.make_property(
            electricity_days_per_week=7,
            water_days_per_week=0,
        )
        property_obj.full_clean()
        property_obj.save()
        self.assertEqual(property_obj.electricity_days_per_week, 7)
        self.assertEqual(property_obj.water_days_per_week, 0)

    def test_electricity_availability_cannot_exceed_seven_days_at_database_level(self):
        property_obj = self.make_property(electricity_days_per_week=8)
        with self.assertRaises(IntegrityError):
            property_obj.save()

    def test_water_availability_cannot_exceed_seven_days_at_database_level(self):
        property_obj = self.make_property(water_days_per_week=8)
        with self.assertRaises(IntegrityError):
            property_obj.save()

    def test_service_source_choices_are_exposed(self):
        property_obj = self.make_property(
            electricity_source='GRID',
            water_source='BOREHOLE',
        )
        property_obj.full_clean()
        property_obj.save()
        self.assertEqual(property_obj.electricity_source, 'GRID')
        self.assertEqual(property_obj.water_source, 'BOREHOLE')
