from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Property
from .location_models import LocationNode, PropertyLocation


@receiver(post_save, sender=Property)
def sync_structured_location(sender, instance, **kwargs):
    province = LocationNode.objects.filter(kind='PROVINCE', active=True, name=instance.province).first()
    if not province:
        return
    level2 = LocationNode.objects.filter(
        parent=province,
        kind__in=['CITY', 'TERRITORY'],
        active=True,
        name=instance.city_or_territory,
    ).first()
    if not level2:
        return
    subdivision = None
    if instance.administrative_subdivision:
        subdivision = LocationNode.objects.filter(
            parent=level2,
            kind__in=['COMMUNE', 'RURAL_COMMUNE', 'SECTOR', 'CHIEFDOM'],
            active=True,
            name=instance.administrative_subdivision,
        ).first()
    PropertyLocation.objects.update_or_create(
        property=instance,
        defaults={
            'province': province,
            'city_or_territory': level2,
            'subdivision': subdivision,
            'neighborhood': instance.neighborhood,
        },
    )
