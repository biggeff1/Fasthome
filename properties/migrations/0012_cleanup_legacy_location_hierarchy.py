from django.db import migrations


class Migration(migrations.Migration):
    """Remove database tables left by the retired parent/child location system.

    The application now stores all location fields directly on Property as free text.
    This migration is intentionally independent of the removed LocationNode and
    PropertyLocation models so it can clean databases that were created with the
    old hierarchy migrations.
    """

    dependencies = [
        ('properties', '0006_property_address_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'DROP TABLE IF EXISTS properties_propertylocation CASCADE; '
                'DROP TABLE IF EXISTS properties_locationnode CASCADE;'
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
