from django.core.management.base import BaseCommand
from django.db import transaction

from properties.location_models import LocationNode, PropertyLocation


class Command(BaseCommand):
    help = "Réinitialise uniquement le référentiel administratif et ses liaisons structurées."

    @transaction.atomic
    def handle(self, *args, **options):
        linked = PropertyLocation.objects.count()
        if linked:
            raise RuntimeError(
                f"Réinitialisation refusée: {linked} propriété(s) utilisent déjà PropertyLocation."
            )

        deleted, _details = LocationNode.objects.all().delete()
        self.stdout.write(self.style.WARNING(f"Référentiel administratif supprimé: {deleted} ligne(s)."))
