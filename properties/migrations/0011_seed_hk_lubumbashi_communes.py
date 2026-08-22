from django.db import migrations


# The current property-location seed contains the Haut-Katanga province and
# the city of Lubumbashi, but 0009 intentionally did not invent subdivision
# names. These are the seven communes of Lubumbashi; Annexe is the
# urbano-rurale commune. The remaining city/territory subdivisions must be
# imported from the authoritative ETD reference before they are added.
LUBUMBASHI_COMMUNES = [
    ('Annexe', 'RURAL_COMMUNE'),
    ('Kamalondo', 'COMMUNE'),
    ('Kampemba', 'COMMUNE'),
    ('Katuba', 'COMMUNE'),
    ('Kenya', 'COMMUNE'),
    ('Lubumbashi', 'COMMUNE'),
    ('Ruashi', 'COMMUNE'),
]


def seed_lubumbashi_communes(apps, schema_editor):
    LocationNode = apps.get_model('properties', 'LocationNode')
    province = LocationNode.objects.filter(kind='PROVINCE', name='Haut-Katanga').first()
    if province is None:
        return
    city = LocationNode.objects.filter(kind='CITY', name='Lubumbashi', parent=province).first()
    if city is None:
        return
    for order, (name, kind) in enumerate(LUBUMBASHI_COMMUNES, 1):
        LocationNode.objects.get_or_create(
            parent=city,
            kind=kind,
            name=name,
            defaults={'order': order, 'active': True},
        )


class Migration(migrations.Migration):
    dependencies = [('properties', '0010_rename_properties_l_kind_9b5f6a_idx_properties__kind_9e1bf1_idx_and_more')]
    operations = [migrations.RunPython(seed_lubumbashi_communes, migrations.RunPython.noop)]
