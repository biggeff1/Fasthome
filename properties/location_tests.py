from django.test import TestCase

from .location_models import LocationNode, PropertyLocation
from .models import Property, PropertyType


class AdministrativeLocationTests(TestCase):
    def setUp(self):
        self.province = LocationNode.objects.create(name='Test Province', kind='PROVINCE')
        self.city = LocationNode.objects.create(name='Test City', kind='CITY', parent=self.province)
        self.territory = LocationNode.objects.create(name='Test Territory', kind='TERRITORY', parent=self.province)
        self.commune = LocationNode.objects.create(name='Test Commune', kind='COMMUNE', parent=self.city)
        self.rural = LocationNode.objects.create(name='Test Rural Commune', kind='RURAL_COMMUNE', parent=self.territory)
        self.sector = LocationNode.objects.create(name='Test Sector', kind='SECTOR', parent=self.territory)
        self.chefferie = LocationNode.objects.create(name='Test Chefferie', kind='CHIEFDOM', parent=self.territory)

    def test_city_children_are_limited_to_that_province(self):
        other = LocationNode.objects.create(name='Other Province', kind='PROVINCE')
        LocationNode.objects.create(name='Other City', kind='CITY', parent=other)
        self.assertEqual(list(self.province.children.filter(kind='CITY').values_list('name', flat=True)), ['Test City'])

    def test_territory_exposes_all_supported_subdivision_kinds(self):
        kinds = set(self.territory.children.values_list('kind', flat=True))
        self.assertEqual(kinds, {'RURAL_COMMUNE', 'SECTOR', 'CHIEFDOM'})

    def test_structured_location_keeps_parent_chain(self):
        property_type = PropertyType.objects.create(name='Location test type')
        user = self._user()
        property_obj = Property.objects.create(
            owner=user,
            property_type=property_type,
            province=self.province.name,
            city_or_territory=self.territory.name,
            administrative_subdivision=self.sector.name,
        )
        structured = PropertyLocation.objects.create(
            property=property_obj,
            province=self.province,
            city_or_territory=self.territory,
            subdivision=self.sector,
            neighborhood='Quartier test',
        )
        self.assertEqual(structured.province.parent, None)
        self.assertEqual(structured.city_or_territory.parent, self.province)
        self.assertEqual(structured.subdivision.parent, self.territory)

    def _user(self):
        from users.models import User
        return User.objects.create_user(
            email='location-tests@example.com',
            password='A-secure-password-123',
            phone='+243900001003',
            last_name='Location',
            first_name='Test',
        )
