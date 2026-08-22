from django.db import migrations


# Historical migrations 0007/0009 seeded an intentionally incomplete
# administrative tree. The authoritative importer now owns the reference.
def noop(apps, schema_editor):
    # Do not delete rows here: existing PropertyLocation links must remain
    # intact. The management command provides an explicit, guarded reset.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('properties', '0010_rename_properties_l_kind_9b5f6a_idx_properties__kind_9e1bf1_idx_and_more'),
    ]
    operations = [
        migrations.RunPython(noop, migrations.RunPython.noop),
    ]
