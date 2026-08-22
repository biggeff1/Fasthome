import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import RequestFactory, TestCase
from django.utils.datastructures import MultiValueDict

from users.models import User

from .models import Property, PropertyPhoto, PropertyType
from .views import _save_photos


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


class PropertyDynamicPhotoUploadTests(TestCase):
    PNG_1X1 = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
    )

    def setUp(self):
        self.user = User.objects.create_user(
            email='photo-tests@example.com',
            password='A-secure-password-123',
            phone='+243900001002',
            last_name='Photo',
            first_name='Test',
            is_certified=True,
        )
        self.property_type = PropertyType.objects.create(name='Maison photo test')
        self.property = Property.objects.create(
            owner=self.user,
            property_type=self.property_type,
            province='Haut-Katanga',
            city_or_territory='Lubumbashi',
            bedroom_count=2,
            living_room_count=1,
            bathroom_count=1,
            toilet_count=1,
            has_kitchen=True,
        )

    def upload(self, name):
        return SimpleUploadedFile(name, self.PNG_1X1, content_type='image/png')

    def request_with_files(self, files):
        request = RequestFactory().post('/properties/create/', data={})
        request.FILES = MultiValueDict(files)
        return request

    def test_photos_are_saved_to_the_declared_room(self):
        request = self.request_with_files({
            'photos_exterior': [self.upload('exterior.png')],
            'photos_bedroom_1': [self.upload('bedroom-1-a.png'), self.upload('bedroom-1-b.png')],
            'photos_bedroom_2': [self.upload('bedroom-2.png')],
            'photos_living_room_1': [self.upload('living.png')],
            'photos_kitchen': [self.upload('kitchen.png')],
        })
        post = {
            'bedroom_count': '2',
            'living_room_count': '1',
            'bathroom_count': '1',
            'toilet_count': '1',
            'has_kitchen': 'yes',
        }

        _save_photos(self.property, request, post)

        self.assertEqual(self.property.photos.count(), 6)
        self.assertEqual(
            self.property.photos.filter(category='BEDROOM', order=1).count(),
            2,
        )
        self.assertEqual(
            self.property.photos.filter(category='BEDROOM', order=2).count(),
            1,
        )
        self.assertEqual(
            self.property.photos.filter(category='LIVING_ROOM', order=1).count(),
            1,
        )
        self.assertEqual(
            self.property.photos.filter(category='KITCHEN', order=1).count(),
            1,
        )
        self.assertEqual(
            self.property.photos.filter(category='EXTERIOR', order=1).count(),
            1,
        )
        self.assertTrue(self.property.photos.get(category='EXTERIOR', order=1).is_primary)

    def test_each_declared_zone_is_limited_to_five_photos(self):
        request = self.request_with_files({
            'photos_bedroom_1': [self.upload(f'bedroom-{i}.png') for i in range(6)],
        })
        post = {
            'bedroom_count': '1',
            'living_room_count': '0',
            'bathroom_count': '0',
            'toilet_count': '0',
            'has_kitchen': 'no',
        }

        with self.assertRaisesMessage(Exception, 'Chambre 1 : maximum 5 photos.'):
            _save_photos(self.property, request, post)
        self.assertEqual(PropertyPhoto.objects.filter(property=self.property).count(), 0)

    def test_total_photo_limit_is_enforced(self):
        for i in range(40):
            PropertyPhoto.objects.create(
                property=self.property,
                image=self.upload(f'existing-{i}.png'),
                category='BEDROOM',
                order=1,
            )

        request = self.request_with_files({
            'photos_exterior': [self.upload('extra.png')],
        })
        post = {
            'bedroom_count': '1',
            'living_room_count': '0',
            'bathroom_count': '0',
            'toilet_count': '0',
            'has_kitchen': 'no',
        }

        with self.assertRaisesMessage(Exception, 'Maximum 40 photos par logement.'):
            _save_photos(self.property, request, post)
