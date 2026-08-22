from django.db import migrations


def sync_property_locations(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    LocationNode = apps.get_model('properties', 'LocationNode')
    PropertyLocation = apps.get_model('properties', 'PropertyLocation')

    for prop in Property.objects.all().iterator():
        province = LocationNode.objects.filter(
            kind='PROVINCE', active=True, parent__isnull=True, name=prop.province
        ).first()
        if not province:
            continue
        level2 = LocationNode.objects.filter(
            parent=province,
            kind__in=['CITY', 'TERRITORY'],
            active=True,
            name=prop.city_or_territory,
        ).first()
        if not level2:
            continue
        subdivision = None
        if prop.administrative_subdivision:
            subdivision = LocationNode.objects.filter(
                parent=level2,
                kind__in=['COMMUNE', 'RURAL_COMMUNE', 'SECTOR', 'CHIEFDOM'],
                active=True,
                name=prop.administrative_subdivision,
            ).first()
        PropertyLocation.objects.update_or_create(
            property_id=prop.pk,
            defaults={
                'province_id': province.pk,
                'city_or_territory_id': level2.pk,
                'subdivision_id': subdivision.pk if subdivision else None,
                'neighborhood': prop.neighborhood,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0007_location_hierarchy'),
    ]

    operations = [
        migrations.RunPython(sync_property_locations, migrations.RunPython.noop),
    ]
