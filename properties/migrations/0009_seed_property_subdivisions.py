from django.db import migrations


# Authoritative subdivision seed data should be maintained here once the
# complete administrative reference is imported. This migration intentionally
# does not invent commune/sector/chefferie names.
def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0008_propertylocation_admin_sync'),
    ]

    operations = [
        migrations.RunPython(noop, migrations.RunPython.noop),
    ]
