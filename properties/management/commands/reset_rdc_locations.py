from django.core.management.base import BaseCommand
from django.db import transaction

from properties.location_models import LocationNode, PropertyLocation


class Command(BaseCommand):
    help = "Supprime le référentiel administratif de test uniquement lorsque les liaisons structurées sont absentes."

    @transaction.atomic
    def handle(self, *args, **options):
        linked = PropertyLocation.objects.count()
        if linked:
            self.stdout.write(
                self.style.WARNING(
                    f"Réinitialisation impossible: {linked} PropertyLocation existe(nt). "
                    "Les données immobilières sont protégées."
                )
            )
            return

        deleted, _details = LocationNode.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Référentiel administratif supprimé: {deleted} ligne(s)."
            )
        )
