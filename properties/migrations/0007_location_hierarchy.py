from django.db import migrations, models


PROVINCES = [
    ('Bas-Uele', 'Buta'), ('Équateur', 'Mbandaka'), ('Haut-Katanga', 'Lubumbashi'), ('Haut-Lomami', 'Kamina'),
    ('Haut-Uele', 'Isiro'), ('Ituri', 'Bunia'), ('Kasaï', 'Tshikapa'), ('Kasaï-Central', 'Kananga'),
    ('Kasaï-Oriental', 'Mbuji-Mayi'), ('Kinshasa', 'Kinshasa'), ('Kongo Central', 'Matadi'), ('Kwango', 'Kenge'),
    ('Kwilu', 'Bandundu'), ('Lomami', 'Kabinda'), ('Lualaba', 'Kolwezi'), ('Mai-Ndombe', 'Inongo'),
    ('Maniema', 'Kindu'), ('Mongala', 'Lisala'), ('Nord-Kivu', 'Goma'), ('Nord-Ubangi', 'Gbadolite'),
    ('Sankuru', 'Lusambo'), ('Sud-Kivu', 'Bukavu'), ('Sud-Ubangi', 'Gemena'), ('Tanganyika', 'Kalemie'),
    ('Tshopo', 'Kisangani'), ('Tshuapa', 'Boende'),
]

CITIES = [
    ('Kinshasa', 'Kinshasa'), ('Bas-Uele', 'Buta'), ('Équateur', 'Mbandaka'),
    ('Haut-Katanga', 'Lubumbashi'), ('Haut-Katanga', 'Likasi'), ('Haut-Katanga', 'Kipushi'),
    ('Haut-Lomami', 'Kamina'), ('Haut-Uele', 'Isiro'), ('Ituri', 'Bunia'), ('Kasaï', 'Tshikapa'),
    ('Kasaï-Central', 'Kananga'), ('Kasaï-Oriental', 'Mbuji-Mayi'), ('Kongo Central', 'Matadi'),
    ('Kongo Central', 'Boma'), ('Kongo Central', 'Mbanza-Ngungu'), ('Kwango', 'Kenge'),
    ('Kwilu', 'Bandundu'), ('Kwilu', 'Kikwit'), ('Lomami', 'Kabinda'), ('Lomami', 'Mwene-Ditu'),
    ('Lualaba', 'Kolwezi'), ('Mai-Ndombe', 'Inongo'), ('Maniema', 'Kindu'), ('Mongala', 'Lisala'),
    ('Mongala', 'Bumba'), ('Nord-Kivu', 'Goma'), ('Nord-Kivu', 'Beni'), ('Nord-Kivu', 'Butembo'),
    ('Nord-Ubangi', 'Gbadolite'), ('Sankuru', 'Lusambo'), ('Sud-Kivu', 'Bukavu'), ('Sud-Kivu', 'Baraka'),
    ('Sud-Kivu', 'Uvira'), ('Sud-Kivu', 'Kamituga'), ('Sud-Ubangi', 'Gemena'), ('Sud-Ubangi', 'Zongo'),
    ('Tanganyika', 'Kalemie'), ('Tshopo', 'Kisangani'), ('Tshuapa', 'Boende'),
]

TERRITORIES = [
    ('Bas-Uele','Aketi'),('Bas-Uele','Ango'),('Bas-Uele','Bambesa'),('Bas-Uele','Bondo'),('Bas-Uele','Buta'),('Bas-Uele','Poko'),
    ('Ituri','Aru'),('Ituri','Djugu'),('Ituri','Irumu'),('Ituri','Mahagi'),('Ituri','Mambasa'),
    ('Tshopo','Bafwasende'),('Tshopo','Banalia'),('Tshopo','Basoko'),('Tshopo','Isangi'),('Tshopo','Opala'),('Tshopo','Ubundu'),('Tshopo','Yahuma'),
    ('Kwilu','Bagata'),('Kwilu','Bulungu'),('Kwilu','Gungu'),('Kwilu','Idiofa'),('Kwilu','Masi-Manimba'),
    ('Équateur','Basankusu'),('Équateur','Bikoro'),('Équateur','Bolomba'),('Équateur','Bomongo'),('Équateur','Ingende'),('Équateur','Lukolela'),('Équateur','Makanza'),
    ('Tshuapa','Befale'),('Tshuapa','Boende'),('Tshuapa','Bokungu'),('Tshuapa','Djolu'),('Tshuapa','Ikela'),('Tshuapa','Monkoto'),
    ('Nord-Kivu','Beni'),('Nord-Kivu','Lubero'),('Nord-Kivu','Masisi'),('Nord-Kivu','Nyiragongo'),('Nord-Kivu','Rutshuru'),('Nord-Kivu','Walikale'),
    ('Mai-Ndombe','Bolobo'),('Mai-Ndombe','Inongo'),('Mai-Ndombe','Kiri'),('Mai-Ndombe','Kutu'),('Mai-Ndombe','Kwamouth'),('Mai-Ndombe','Mushie'),('Mai-Ndombe','Oshwe'),('Mai-Ndombe','Yumbi'),
    ('Mongala','Bongandanga'),('Mongala','Bumba'),('Mongala','Lisala'),
    ('Nord-Ubangi','Bosobolo'),('Nord-Ubangi','Businga'),('Nord-Ubangi','Mobayi-Mbongo'),('Nord-Ubangi','Yakoma'),
    ('Sud-Ubangi','Budjala'),('Sud-Ubangi','Gemena'),('Sud-Ubangi','Kungu'),('Sud-Ubangi','Libenge'),
    ('Haut-Lomami','Bukama'),('Haut-Lomami','Kabongo'),('Haut-Lomami','Kamina'),('Haut-Lomami','Kanyama'),('Haut-Lomami','Malemba-Nkulu'),
    ('Kasaï','Dekese'),('Kasaï','Ilebo'),('Kasaï','Kamonia'),('Kasaï','Luebo'),('Kasaï','Mweka'),
    ('Kasaï-Central','Demba'),('Kasaï-Central','Dibaya'),('Kasaï-Central','Dimbelenge'),('Kasaï-Central','Kazumba'),('Kasaï-Central','Luiza'),
    ('Lualaba','Dilolo'),('Lualaba','Kapanga'),('Lualaba','Lubudi'),('Lualaba','Mutshatsha'),('Lualaba','Sandoa'),
    ('Haut-Uele','Dungu'),('Haut-Uele','Faradje'),('Haut-Uele','Niangara'),('Haut-Uele','Rungu'),('Haut-Uele','Wamba'),('Haut-Uele','Watsa'),
    ('Kwango','Feshi'),('Kwango','Kahemba'),('Kwango','Kasongo-Lunda'),('Kwango','Kenge'),('Kwango','Popokabaka'),
    ('Sud-Kivu','Fizi'),('Sud-Kivu','Idjwi'),('Sud-Kivu','Kabare'),('Sud-Kivu','Kalehe'),('Sud-Kivu','Mwenga'),('Sud-Kivu','Shabunda'),('Sud-Kivu','Uvira'),('Sud-Kivu','Walungu'),
    ('Lomami','Gandajika'),('Lomami','Kabinda'),('Lomami','Kamiji'),('Lomami','Lubao'),('Lomami','Luilu'),
    ('Tanganyika','Kabalo'),('Tanganyika','Kalemie'),('Tanganyika','Kongolo'),('Tanganyika','Manono'),('Tanganyika','Moba'),('Tanganyika','Nyunzu'),
    ('Maniema','Kabambare'),('Maniema','Kailo'),('Maniema','Kasongo'),('Maniema','Kibombo'),('Maniema','Lubutu'),('Maniema','Pangi'),('Maniema','Punia'),
    ('Kasaï-Oriental','Kabeya-Kamwanga'),('Kasaï-Oriental','Katanda'),('Kasaï-Oriental','Lupatapata'),('Kasaï-Oriental','Miabi'),('Kasaï-Oriental','Tshilenge'),
    ('Haut-Katanga','Kambove'),('Haut-Katanga','Kasenga'),('Haut-Katanga','Kipushi'),('Haut-Katanga','Mitwaba'),('Haut-Katanga','Pweto'),('Haut-Katanga','Sakania'),
    ('Sankuru','Katako-Kombe'),('Sankuru','Kole'),('Sankuru','Lodja'),('Sankuru','Lomela'),('Sankuru','Lubefu'),('Sankuru','Lusambo'),
    ('Kongo Central','Kasangulu'),('Kongo Central','Kimvula'),('Kongo Central','Lukula'),('Kongo Central','Luozi'),('Kongo Central','Madimba'),('Kongo Central','Mbanza-Ngungu'),('Kongo Central','Moanda'),('Kongo Central','Seke-Banza'),('Kongo Central','Songololo'),('Kongo Central','Tshela'),
]


def seed_locations(apps, schema_editor):
    LocationNode = apps.get_model('properties', 'LocationNode')
    provinces = {}
    for order, (name, capital) in enumerate(PROVINCES, 1):
        province, _ = LocationNode.objects.get_or_create(parent=None, kind='PROVINCE', name=name, defaults={'order': order, 'code': name.upper().replace(' ', '_')})
        provinces[name] = province
    for order, (province_name, city_name) in enumerate(CITIES, 1):
        LocationNode.objects.get_or_create(parent=provinces[province_name], kind='CITY', name=city_name, defaults={'order': order})
    for order, (province_name, territory_name) in enumerate(TERRITORIES, 1):
        LocationNode.objects.get_or_create(parent=provinces[province_name], kind='TERRITORY', name=territory_name, defaults={'order': order})


class Migration(migrations.Migration):
    dependencies = [('properties', '0006_property_address_fields')]
    operations = [
        migrations.CreateModel(
            name='LocationNode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('kind', models.CharField(choices=[('PROVINCE','Province'),('CITY','Ville'),('TERRITORY','Territoire'),('COMMUNE','Commune'),('RURAL_COMMUNE','Commune rurale'),('SECTOR','Secteur'),('CHIEFDOM','Chefferie')], max_length=20)),
                ('code', models.CharField(blank=True, max_length=40)),
                ('active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='children', to='properties.locationnode')),
            ],
            options={'ordering': ['order', 'name']},
        ),
        migrations.CreateModel(
            name='PropertyLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('neighborhood', models.CharField(blank=True, max_length=160)),
                ('city_or_territory', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='property_locations_as_level2', to='properties.locationnode')),
                ('province', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='property_locations_as_province', to='properties.locationnode')),
                ('subdivision', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='property_locations_as_subdivision', to='properties.locationnode')),
                ('property', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='structured_location', to='properties.property')),
            ],
        ),
        migrations.AddIndex(model_name='locationnode', index=models.Index(fields=['kind','parent','active'], name='properties_l_kind_9b5f6a_idx')),
        migrations.AddIndex(model_name='locationnode', index=models.Index(fields=['parent','active'], name='properties_l_parent_2c4c5b_idx')),
        migrations.AddConstraint(model_name='locationnode', constraint=models.UniqueConstraint(fields=('parent','kind','name'), name='unique_location_child')),
        migrations.RunPython(seed_locations, migrations.RunPython.noop),
    ]
