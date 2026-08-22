from django.db import models


class LocationNode(models.Model):
    KIND_CHOICES = [
        ('PROVINCE', 'Province'),
        ('CITY', 'Ville'),
        ('TERRITORY', 'Territoire'),
        ('COMMUNE', 'Commune'),
        ('RURAL_COMMUNE', 'Commune rurale'),
        ('SECTOR', 'Secteur'),
        ('CHIEFDOM', 'Chefferie'),
    ]
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    code = models.CharField(max_length=40, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = 'properties'
        ordering = ['order', 'name']
        constraints = [
            models.UniqueConstraint(fields=('parent', 'kind', 'name'), name='unique_location_child'),
        ]
        indexes = [
            models.Index(fields=('kind', 'parent', 'active')),
            models.Index(fields=('parent', 'active')),
        ]

    def __str__(self):
        return self.name


class PropertyLocation(models.Model):
    property = models.OneToOneField('properties.Property', on_delete=models.CASCADE, related_name='structured_location')
    province = models.ForeignKey(LocationNode, on_delete=models.PROTECT, related_name='property_locations_as_province')
    city_or_territory = models.ForeignKey(LocationNode, on_delete=models.PROTECT, related_name='property_locations_as_level2')
    subdivision = models.ForeignKey(LocationNode, on_delete=models.PROTECT, related_name='property_locations_as_subdivision', null=True, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)

    class Meta:
        app_label = 'properties'

    def __str__(self):
        return f'{self.province} / {self.city_or_territory}'
