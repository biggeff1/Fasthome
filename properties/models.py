import uuid
from django.conf import settings
from django.db import models


def code(prefix: str):
    return f'{prefix}-{uuid.uuid4().hex[:10].upper()}'


class PropertyType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['order', 'name']
    def __str__(self):
        return self.name


class Property(models.Model):
    STATUS = [('DRAFT', 'Brouillon'), ('UNDER_REVIEW', 'En vérification'), ('AVAILABLE', 'Disponible'), ('RENTED', 'Loué'), ('SUSPENDED', 'Suspendu'), ('CLOSED', 'Clôturé')]
    property_id = models.CharField(max_length=32, unique=True, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='properties')
    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT)
    furnished = models.BooleanField(default=False)
    province = models.CharField(max_length=100)
    city_or_territory = models.CharField(max_length=120)
    administrative_subdivision = models.CharField(max_length=160, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)
    exact_address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    google_maps_url = models.URLField(blank=True)
    bedroom_count = models.PositiveIntegerField(default=0)
    living_room_count = models.PositiveIntegerField(default=0)
    has_kitchen = models.BooleanField(default=False)
    bathroom_count = models.PositiveIntegerField(default=0)
    toilet_count = models.PositiveIntegerField(default=0)
    floor = models.CharField(max_length=80, blank=True)
    ceiling_type = models.CharField(max_length=100, blank=True)
    floor_type = models.CharField(max_length=100, blank=True)
    monthly_rent = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    guarantee_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    max_occupants = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    furniture_condition = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.property_id:
            self.property_id = code('FP')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.property_id} - {self.property_type}'


class PropertyFeature(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='features')
    key = models.CharField(max_length=80)
    value = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=60, blank=True)


class Bedroom(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bedrooms')
    number = models.PositiveIntegerField()
    bed_type = models.CharField(max_length=50, blank=True)
    mattress = models.BooleanField(default=False)
    wardrobe = models.BooleanField(default=False)
    bedside_table = models.BooleanField(default=False)
    desk = models.BooleanField(default=False)
    chair = models.BooleanField(default=False)
    curtains = models.BooleanField(default=False)
    mosquito_net = models.BooleanField(default=False)
    fan = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)


class LivingRoom(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='living_rooms')
    number = models.PositiveIntegerField()
    sofa = models.BooleanField(default=False)
    coffee_table = models.BooleanField(default=False)
    tv_cabinet = models.BooleanField(default=False)
    television = models.BooleanField(default=False)
    curtains = models.BooleanField(default=False)
    fan = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)


class Kitchen(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='kitchen')
    equipped = models.BooleanField(default=False)
    stove = models.BooleanField(default=False)
    oven = models.BooleanField(default=False)
    refrigerator = models.BooleanField(default=False)
    freezer = models.BooleanField(default=False)
    microwave = models.BooleanField(default=False)
    hood = models.BooleanField(default=False)
    sink = models.BooleanField(default=False)
    cupboards = models.BooleanField(default=False)
    table = models.BooleanField(default=False)
    chairs = models.BooleanField(default=False)


class Bathroom(models.Model):
    LOCATION = [('INTERIOR', 'Intérieure'), ('EXTERIOR', 'Extérieure')]
    ACCESS = [('PRIVATE', 'Privée'), ('PUBLIC', 'Publique / commune')]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bathrooms')
    number = models.PositiveIntegerField()
    location_type = models.CharField(max_length=10, choices=LOCATION)
    access_type = models.CharField(max_length=10, choices=ACCESS, blank=True)
    hot_water = models.BooleanField(default=False)
    shower = models.BooleanField(default=False)
    bathtub = models.BooleanField(default=False)
    sink = models.BooleanField(default=False)
    mirror = models.BooleanField(default=False)
    storage = models.BooleanField(default=False)


class Toilet(models.Model):
    LOCATION = [('INTERIOR', 'Intérieure'), ('EXTERIOR', 'Extérieure')]
    ACCESS = [('PRIVATE', 'Privée'), ('PUBLIC', 'Publique / commune')]
    TYPES = [('BOWL', 'Cuve'), ('TURKISH', 'Turque'), ('OTHER', 'Autre')]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='toilets')
    number = models.PositiveIntegerField()
    location_type = models.CharField(max_length=10, choices=LOCATION)
    access_type = models.CharField(max_length=10, choices=ACCESS, blank=True)
    toilet_type = models.CharField(max_length=10, choices=TYPES)


class PropertyPhoto(models.Model):
    CATEGORIES = [('GENERAL', 'Générale'), ('EXTERIOR', 'Extérieur'), ('LIVING_ROOM', 'Salon'), ('BEDROOM', 'Chambre'), ('KITCHEN', 'Cuisine'), ('BATHROOM', 'Salle de bain'), ('TOILET', 'Toilette'), ('PARKING', 'Parking'), ('GARDEN', 'Jardin'), ('OTHER', 'Autre')]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='properties/photos/')
    category = models.CharField(max_length=20, choices=CATEGORIES, default='GENERAL')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)


class PropertyPublication(models.Model):
    STATUS = [('DRAFT', 'Brouillon'), ('SUBMITTED', 'Soumis'), ('UNDER_REVIEW', 'En vérification'), ('CORRECTION_REQUIRED', 'À corriger'), ('PUBLISHED', 'Publié'), ('SUSPENDED', 'Suspendu'), ('RENTED', 'Loué')]
    publication_id = models.CharField(max_length=32, unique=True, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='publication')
    status = models.CharField(max_length=25, choices=STATUS, default='DRAFT')
    correction_message = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.publication_id:
            self.publication_id = code('PUB')
        super().save(*args, **kwargs)


class PropertyDeclaration(models.Model):
    publication = models.OneToOneField(PropertyPublication, on_delete=models.CASCADE, related_name='declaration')
    relationship_to_property = models.CharField(max_length=80)
    right_to_offer_confirmed = models.BooleanField(default=False)
    accuracy_confirmed = models.BooleanField(default=False)
    photos_authentic_confirmed = models.BooleanField(default=False)
    authorization_confirmed = models.BooleanField(default=False)
    acknowledged_responsibility = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)


class CollaborationConsent(models.Model):
    publication = models.OneToOneField(PropertyPublication, on_delete=models.CASCADE, related_name='collaboration_consent')
    verification_accepted = models.BooleanField(default=False)
    presentation_accepted = models.BooleanField(default=False)
    visits_accepted = models.BooleanField(default=False)
    management_accepted = models.BooleanField(default=False)
    collaboration_accepted = models.BooleanField(default=False)
    terms_version = models.CharField(max_length=50)
    accepted_at = models.DateTimeField(null=True, blank=True)


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'property'], name='unique_favorite')]
