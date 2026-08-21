from decimal import Decimal

from django.test import TestCase

from properties.models import Property, PropertyType
from .models import SearchRequest
from .views import score_property


class MatchingCriteriaTests(TestCase):
    def setUp(self):
        property_type = PropertyType.objects.create(name='Appartement matching')
        self.property = Property.objects.create(
            owner_id=None,
            property_type=property_type,
            furnished=True,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            administrative_subdivision='Commune Lubumbashi',
            neighborhood='Golf',
            bedroom_count=3,
            living_room_count=2,
            max_occupants=5,
            monthly_rent=Decimal('350000'),
            status='AVAILABLE',
        )

    def test_matching_uses_only_defined_criteria_and_normalizes_text(self):
        search = SearchRequest.objects.create(
            furnished_preference='YES',
            province='haut-katanga',
            city_or_territory='LUBUMBASHI',
            administrative_subdivision='Commune Lubumbashi',
            neighborhood='golf',
            minimum_living_rooms=2,
            minimum_bedrooms=3,
            maximum_budget=Decimal('400000'),
            requested_occupants=4,
        )
        score, breakdown = score_property(self.property, search)
        self.assertEqual(score, Decimal('100'))
        self.assertEqual(set(breakdown), {'budget', 'province', 'city', 'subdivision', 'neighborhood', 'bedrooms', 'living_rooms', 'furnished', 'occupants'})

    def test_neighborhood_typo_can_still_match(self):
        search = SearchRequest.objects.create(
            furnished_preference='ANY',
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            neighborhood='Gollf',
            requested_occupants=1,
        )
        score, breakdown = score_property(self.property, search)
        self.assertEqual(breakdown['neighborhood'], 100)
        self.assertGreaterEqual(score, Decimal('70'))
